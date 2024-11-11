from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from gpt_rag import *
from pdf import *
from gpt_rag import *
from embedding import *
from gpt_rag_asyncio import *
import argparse
import os
from requests import Session
from typing import Generator, Union
from pymongo import MongoClient
from call_mongodb import *
from tqdm import tqdm
from download_paper_ss import *
import urllib3
from search_ss import *
import asyncio
import certifi
urllib3.disable_warnings()

S2_API_KEY = os.getenv('x-api-key')

uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
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




def search_and_retrieve_keyword(collection_name, collection1_name,p=None):
    collection=db[collection_name]
    collection1=collection1_name
    documents = list(collection.find({}, {'_id': 1, 'Reference article name': 1, 'Reference text in main article': 1, 'Date': 1 }))
    df = pd.DataFrame(documents)
    """Keep only latest date"""
    # Convert 'Date' column to numeric to enable comparison
    df['Date'] = pd.to_numeric(df['Date'], errors='coerce')

    # Drop rows where 'Date' is NaN (if conversion fails for some entries)
    df = df.dropna(subset=['Date'])

    # Sort by 'Reference text in main article' and 'Date' in descending order
    df = df.sort_values(by=['Reference text in main article', 'Date'], ascending=[True, False])

    # Drop duplicates, keeping only the first (latest) entry for each unique 'Reference text in main article'
    df_latest = df.drop_duplicates(subset=['Reference text in main article'], keep='first')


    # Reset index for cleanliness (optional)
    df_latest.reset_index(drop=True, inplace=True)
    print("Running async process on dataframe rows...")
    keywords = asyncio.run(async_process_dataframe(df_latest,p))

    # Create a list of tuples to integrate keywords with existing data
    nametextdate = []
    for index, row in df_latest.iterrows():
        name = row['Reference article name']
        text = row['Reference text in main article']
        date = row['Date']
        keyword = keywords[index]  # Use the corresponding keyword returned from async function
        nametextdate.append([name, text, date, keyword])

    download = []
    ext_id = []
    field = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess,authors'
    
    # Continue with the existing logic using the `nametextdate` that now includes keywords
    for ntd in tqdm(nametextdate, desc="Processing references"):
        n = ntd[0]
        t = ntd[1]
        d = ntd[2]
        keyword = ntd[3]
        
        # Proceed with further logic using `keyword` instead of calling `process_row_async` again
        papers = total_search_by_grouped_keywords(keyword, year=d, exclude_name=n, fields=field)
        external_id_list, filtered_metadata_list = preprocess_paper_metadata(papers)
        
        for data in filtered_metadata_list:
            download.append(data)
        
        total = papers
        paper_ids = extract_paper_ids(total)
        title = extract_title(total)
        year = extract_year(total)
        authors = extract_author(total)
        
        paperidandtitleandyearandauthors = []
        for k in range(len(paper_ids)):
            paperidandtitleandyearandauthors.append([paper_ids[k], title[k], year[k],authors[k]])
        
        # Append the paper ID and title information to `ntd`
        ntd.append(paperidandtitleandyearandauthors)
        
        # Collect external IDs for tracking purposes
        for j in external_id_list:
            ext_id.append(j)
    # print(nametextdate)
    # print(download)
    failed_downloads, successful_downloads=asyncio.run(process_and_download(download, directory='papers'))

    
    flattened_data = []
    for row in tqdm(nametextdate, desc="Flattening data"):
        name, text, yearoforiginal, keyword, paper_idsandtitleandyearandauthors= row
        if paper_idsandtitleandyearandauthors:  # If paper_idsandtitle is not empty
            for pidty in paper_idsandtitleandyearandauthors:
                paper_id=pidty[0]
                title=pidty[1]
                year=pidty[2]
                authors=pidty[3]
                flattened_data.append([name, text, yearoforiginal, keyword, paper_id, title,year,authors])
        else:  # If paper_idsandtitle is empty
            flattened_data.append([name, text, yearoforiginal, keyword, '','', '',''])  # Empty cell for paper_id and title


    columns=['Title of original reference article', 'Text in main article referencing reference article', 'Year reference article released', 'Keywords for graph paper search','Paper Id of new reference article found', 'Title of new reference article found','Year new reference article found published','authors']
    df=pd.DataFrame(flattened_data,columns=columns)
    ex_pdf='external_pdfs'
    pdf_folder = 'papers'
    df= update_downloadable_status(df, pdf_folder)
    df=add_external_id_to_undownloadable_papers(df,ext_id)
    df=update_failure_reasons(df, failed_downloads)
    df_updated=add_pdf_url_column(df,download)
    #for now we move after checks to show what semantic scholar api misses out on, but eventually we will move first then update df
    move_pdf_files(ex_pdf, pdf_folder)
    final_ans = 'new_ref_paper_ids_EXT_IDS_check.xlsx'
    send_excel(df_updated, 'RAG', final_ans)
    # Convert DataFrames to records
    records = df_updated.to_dict(orient='records')

    # Save data to MongoDB
    # Track progress for MongoDB operations
    print("Sending data to MongoDB Atlas...")
    replace_database_collection(uri, database, collection1, records)


def search_and_retrieve_keyword_agentic(new_metadata,old_metadata,p=None):
    collection = db['missing']
    collection1 = old_metadata
    collection2 = new_metadata

    # Include 'Reference article name' in your query
    documents = list(collection.find({}, {'_id': 1, 'Reference article name': 1, 'Reference text in main article': 1, 'Date': 1}))
    df = pd.DataFrame(documents)

    # Ensure 'Reference article name' is in the DataFrame
    if 'Reference article name' not in df.columns:
        print("Error: 'Reference article name' not found in the DataFrame.")
        return

    # async function
    keywords = asyncio.run(async_process_dataframe(df, p))

    # Create a list of tuples to integrate keywords with existing data
    nametextdate = []
    for index, row in df.iterrows():
        name = row['Reference article name']
        text = row['Reference text in main article']
        date = row['Date']
        keyword = keywords[index]  # Use the corresponding keyword returned from async function
        nametextdate.append([name, text, date, keyword])

    download = []
    ext_id = []
    field = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess,authors'

    # Initialize a new list to collect additional data
    nametextdate_updated = []

    # Continue with the existing logic using the `nametextdate` that now includes keywords
    for ntd in tqdm(nametextdate, desc="Processing references"):
        n = ntd[0]
        t = ntd[1]
        d = ntd[2]
        keyword = ntd[3]

        # Proceed with further logic using `keyword`
        papers = total_search_by_grouped_keywords(keyword, year=d, exclude_name=n, fields=field)
        external_id_list, filtered_metadata_list = preprocess_paper_metadata(papers)

        download.extend(filtered_metadata_list)
        total = papers
        paper_ids = extract_paper_ids(total)
        titles = extract_title(total)
        years = extract_year(total)
        authors = extract_author(total)

        paperidandtitleandyearandauthors = []
        for k in range(len(paper_ids)):
            paperidandtitleandyearandauthors.append([paper_ids[k], titles[k], years[k],authors[k]])

        # Append the paper ID and title information to `ntd`
        ntd_extended = ntd + [paperidandtitleandyearandauthors]
        nametextdate_updated.append(ntd_extended)

        # Collect external IDs for tracking purposes
        ext_id.extend(external_id_list)

    # Replace the old nametextdate with the updated one
    nametextdate = nametextdate_updated

    failed_downloads, successful_downloads = asyncio.run(process_and_download(download, directory='retry_paper'))

    # Flatten the data
    flattened_data = []
    for row in tqdm(nametextdate, desc="Flattening data"):
        if len(row) == 5:
            name, text, yearoforiginal, keyword, paper_idsandtitleandyearandauthors = row
        else:
            name, text, yearoforiginal, keyword = row
            paper_idsandtitleandyearandauthors = []

        if paper_idsandtitleandyearandauthors:  # If paper_idsandtitleandyear is not empty
            for pidty in paper_idsandtitleandyearandauthors:
                paper_id = pidty[0]
                title = pidty[1]
                year = pidty[2]
                authors = pidty[3]
                flattened_data.append([name, text, yearoforiginal, keyword, paper_id, title, year,authors])
        else:  # If paper_idsandtitleandyear is empty
            flattened_data.append([name, text, yearoforiginal, keyword, '', '', '',''])  # Empty cells

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

    # Move PDF files
    move_pdf_files(ex_pdf, pdf_folder)

    #new data send to excel (new_metadata)
    final_ans = 'new_ref_paper_ids_EXT_IDS_retry.xlsx'
    send_excel(df_updated, 'RAG', final_ans)

    # Convert DataFrames to records
    records = df_updated.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")
    # Ensure 'uri' and 'db' are defined
    # Assuming 'db' is your database object, extract the database name
    database_name = db.name
    # ADD new found meta data to old meta data
    insert_documents(uri, database_name, collection1, records)
    #send new found metat data to a new collection (or replace if alr have)
    replace_database_collection(uri,database_name,collection2,records)
    #output new meta data in df form
    return df_updated



