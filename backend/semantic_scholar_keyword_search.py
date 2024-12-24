from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from .gpt_rag import *
from .pdf import *
from .gpt_rag import *
from .gpt_rag_asyncio import *
import os
from .call_mongodb import *
from tqdm import tqdm
from .download_paper_ss import *
import urllib3
from .search_ss import *
import asyncio
from .mongo_client import MongoDBClient
urllib3.disable_warnings()

S2_API_KEY = os.getenv('x-api-key')

uri = os.getenv("uri_mongo")
client = MongoDBClient.get_client()
db = client['data'] 
database = 'data'
# collection = db['find_ref']
# collection1 ='new_ref_found' #meta data database

async def process_row_async(t, p=None, semaphore=None):
    """Async function to process each row in the DataFrame using the async Azure OpenAI call with a semaphore."""
    
    async with semaphore:  # Acquire the semaphore
        # Use the async wrapper to call the GPT service with retry logic
        ans = await call_keyword_search_async(t, p)
        return ans


async def async_process_dataframe(df_latest, p=None, max_concurrent_tasks=10):
    """Helper function to process the DataFrame asynchronously with a semaphore to limit concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent_tasks)  # Limit concurrency with a semaphore
    tasks = []
    
    for index, row in df_latest.iterrows():
        text = row['Reference text in main article']
        tasks.append(process_row_async(text, p, semaphore))
    
    # Gather all results
    results = await asyncio.gather(*tasks)
    return results



def search_and_retrieve_keyword(collection_name, collection1_name, p=None):
    try:
        delete_folder('papers')
        collection = db[collection_name]
        collection1 = collection1_name
        documents = list(collection.find({}, {
            '_id': 1,
            'Reference article name': 1,
            'Reference text in main article': 1,
            'Date': 1
        }))
        df = pd.DataFrame(documents)
        """Keep only latest date"""
        # Convert 'Date' column to numeric to enable comparison
        df['Date'] = pd.to_numeric(df['Date'], errors='coerce')

        # Drop rows where 'Date' is NaN
        df = df.dropna(subset=['Date'])

        # Sort by 'Reference text in main article' and 'Date' in descending order
        df = df.sort_values(by=['Reference text in main article', 'Date'], ascending=[True, False])

        # Drop duplicates, keeping only the latest entry
        df_latest = df.drop_duplicates(subset=['Reference text in main article'], keep='first')
        df_latest.reset_index(drop=True, inplace=True)

        print("Running async process on dataframe rows...")
        keywords = asyncio.run(async_process_dataframe(df_latest, p))

        # Integrate keywords with the data
        nametextdate = []
        for index, row in df_latest.iterrows():
            name = row['Reference article name']
            text = row['Reference text in main article']
            date = row['Date']
            keyword = keywords[index]
            nametextdate.append([name, text, date, keyword])

        download = []
        ext_id = []
        field = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess,authors'

        # Process references with progress bar
        for ntd in tqdm(nametextdate, desc="Processing references"):
            n = ntd[0]
            t = ntd[1]
            d = ntd[2]
            keyword = ntd[3]

            papers = total_search_by_grouped_keywords(keyword, year=d, exclude_name=n, fields=field)
            external_id_list, filtered_metadata_list = preprocess_paper_metadata(papers)

            download.extend(filtered_metadata_list)
            paper_ids = extract_paper_ids(papers)
            title = extract_title(papers)
            year = extract_year(papers)
            authors = extract_author(papers)

            paperidandtitleandyearandauthors = []
            for k in range(len(paper_ids)):
                paperidandtitleandyearandauthors.append(
                    [paper_ids[k], title[k], year[k], authors[k]]
                )

            ntd.append(paperidandtitleandyearandauthors)
            ext_id.extend(external_id_list)

        failed_downloads, successful_downloads = asyncio.run(process_and_download(download, directory='papers'))

        flattened_data = []
        for row in tqdm(nametextdate, desc="Flattening data"):
            name, text, yearoforiginal, keyword, paper_idsandtitleandyearandauthors = row
            if paper_idsandtitleandyearandauthors:
                for pidty in paper_idsandtitleandyearandauthors:
                    paper_id = pidty[0]
                    title = pidty[1]
                    yr = pidty[2]
                    auth = pidty[3]
                    flattened_data.append([name, text, yearoforiginal, keyword, paper_id, title, yr, auth])
            else:
                flattened_data.append([name, text, yearoforiginal, keyword, '', '', '', ''])

        columns = [
            'Title of original reference article',
            'Text in main article referencing reference article',
            'Year reference article released',
            'Keywords for graph paper search',
            'Paper Id of new reference article found',
            'Title of new reference article found',
            'Year new reference article found published',
            'authors'
        ]
        df = pd.DataFrame(flattened_data, columns=columns)
        ex_pdf = 'external_pdfs'
        pdf_folder = 'papers'
        df = update_downloadable_status(df, pdf_folder)
        df = add_external_id_to_undownloadable_papers(df, ext_id)
        df = update_failure_reasons(df, failed_downloads)
        df_updated = add_pdf_url_column(df, download)

        move_pdf_files(ex_pdf, pdf_folder)

        records = df_updated.to_dict(orient='records')

        print("Sending data to MongoDB Atlas...")
        replace_database_collection(uri, database, collection1, records)

    finally:
        # Force clear any leftover tqdm instances
        tqdm._instances.clear()


def search_and_retrieve_keyword_agentic(new_metadata, old_metadata, p=None):
    try:
        collection = db['missing']
        collection1 = old_metadata
        collection2 = new_metadata

        documents = list(collection.find({}, {
            '_id': 1,
            'Reference article name': 1,
            'Reference text in main article': 1,
            'Date': 1
        }))
        df = pd.DataFrame(documents)

        if 'Reference article name' not in df.columns:
            print("Error: 'Reference article name' not found in the DataFrame.")
            return

        keywords = asyncio.run(async_process_dataframe(df, p))

        nametextdate = []
        for index, row in df.iterrows():
            name = row['Reference article name']
            text = row['Reference text in main article']
            date = row['Date']
            keyword = keywords[index]
            nametextdate.append([name, text, date, keyword])

        download = []
        ext_id = []
        field = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess,authors'

        nametextdate_updated = []
        for ntd in tqdm(nametextdate, desc="Processing references"):
            n = ntd[0]
            t = ntd[1]
            d = ntd[2]
            keyword = ntd[3]

            papers = total_search_by_grouped_keywords(keyword, year=d, exclude_name=n, fields=field)
            external_id_list, filtered_metadata_list = preprocess_paper_metadata(papers)

            download.extend(filtered_metadata_list)
            paper_ids = extract_paper_ids(papers)
            titles = extract_title(papers)
            years = extract_year(papers)
            authors = extract_author(papers)

            paperidandtitleandyearandauthors = []
            for k in range(len(paper_ids)):
                paperidandtitleandyearandauthors.append([paper_ids[k], titles[k], years[k], authors[k]])

            ntd_extended = ntd + [paperidandtitleandyearandauthors]
            nametextdate_updated.append(ntd_extended)
            ext_id.extend(external_id_list)

        nametextdate = nametextdate_updated
        failed_downloads, successful_downloads = asyncio.run(
            process_and_download(download, directory='retry_paper')
        )

        flattened_data = []
        for row in tqdm(nametextdate, desc="Flattening data"):
            # Ensure row has enough elements
            if len(row) == 5:
                name, text, yearoforiginal, keyword, paper_idsandtitleandyearandauthors = row
            else:
                name, text, yearoforiginal, keyword = row[:4]
                paper_idsandtitleandyearandauthors = []

            if paper_idsandtitleandyearandauthors:
                for pidty in paper_idsandtitleandyearandauthors:
                    paper_id = pidty[0]
                    title = pidty[1]
                    yr = pidty[2]
                    auth = pidty[3]
                    flattened_data.append([name, text, yearoforiginal, keyword, paper_id, title, yr, auth])
            else:
                flattened_data.append([name, text, yearoforiginal, keyword, '', '', '', ''])

        columns = [
            'Title of original reference article',
            'Text in main article referencing reference article',
            'Year reference article released',
            'Keywords for graph paper search',
            'Paper Id of new reference article found',
            'Title of new reference article found',
            'Year new reference article found published',
            'authors'
        ]
        df = pd.DataFrame(flattened_data, columns=columns)
        ex_pdf = 'external_pdfs'
        pdf_folder = 'retry_paper'
        df = update_downloadable_status(df, pdf_folder)
        df = add_external_id_to_undownloadable_papers(df, ext_id)
        df = update_failure_reasons(df, failed_downloads)
        df_updated = add_pdf_url_column(df, download)

        move_pdf_files(ex_pdf, pdf_folder)

        records = df_updated.to_dict(orient='records')

        print("Sending data to MongoDB Atlas...")
        database_name = db.name

        # Insert data into old metadata
        insert_documents(uri, database_name, collection1, records)
        # Replace data in new metadata
        replace_database_collection(uri, database_name, collection2, records)

        return df_updated

    finally:
        # Force clear any leftover tqdm instances
        tqdm._instances.clear()
