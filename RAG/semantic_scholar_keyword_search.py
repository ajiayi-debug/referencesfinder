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

async def process_row_async(t):
    """Async function to process each row in the DataFrame using the async Azure OpenAI call."""
    
    
    # Use the async wrapper to call the GPT service with retry logic
    ans = await call_keyword_search_async(t)
    print(ans)
    return ans


async def async_process_dataframe(df_latest):
    """Helper function to process the DataFrame asynchronously."""
    tasks = []
    for index, row in df_latest.iterrows():
        text = row['Reference text in main article']
        tasks.append(process_row_async(text))
    # Gather all results
    results = await asyncio.gather(*tasks)
    return results




def search_and_retrieve_keyword(collection_name, collection1_name):
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
    keywords = asyncio.run(async_process_dataframe(df_latest))

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
    field = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess'
    
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
        
        paperidandtitleandyear = []
        for k in range(len(paper_ids)):
            paperidandtitleandyear.append([paper_ids[k], title[k], year[k]])
        
        # Append the paper ID and title information to `ntd`
        ntd.append(paperidandtitleandyear)
        
        # Collect external IDs for tracking purposes
        for j in external_id_list:
            ext_id.append(j)
    # print(nametextdate)
    # print(download)
    failed_downloads, successful_downloads=asyncio.run(process_and_download(download, directory='papers'))

    
    flattened_data = []
    for row in tqdm(nametextdate, desc="Flattening data"):
        name, text, yearoforiginal, keyword, paper_idsandtitleandyear= row
        if paper_idsandtitleandyear:  # If paper_idsandtitle is not empty
            for pidty in paper_idsandtitleandyear:
                paper_id=pidty[0]
                title=pidty[1]
                year=pidty[2]
                flattened_data.append([name, text, yearoforiginal, keyword, paper_id, title,year])
        else:  # If paper_idsandtitle is empty
            flattened_data.append([name, text, yearoforiginal, keyword, '','', ''])  # Empty cell for paper_id and title


    columns=['Title of original reference article', 'Text in main article referencing reference article', 'Year reference article released', 'Keywords for graph paper search','Paper Id of new reference article found', 'Title of new reference article found','Year new reference article found published']
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

#test for 5 statements

def test_search_and_retrieve_keyword(collection_name, collection1_name, test):
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
    df_top5=df_latest.head(test)
    print("Running async process on dataframe rows...")
    keywords = asyncio.run(async_process_dataframe(df_top5))

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
    field = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess'
    
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
        
        paperidandtitleandyear = []
        for k in range(len(paper_ids)):
            paperidandtitleandyear.append([paper_ids[k], title[k], year[k]])
        
        # Append the paper ID and title information to `ntd`
        ntd.append(paperidandtitleandyear)
        
        # Collect external IDs for tracking purposes
        for j in external_id_list:
            ext_id.append(j)
    # print(nametextdate)
    # print(download)
    failed_downloads, successful_downloads=asyncio.run(process_and_download(download, directory='papers'))

    
    flattened_data = []
    for row in tqdm(nametextdate, desc="Flattening data"):
        name, text, yearoforiginal, keyword, paper_idsandtitleandyear= row
        if paper_idsandtitleandyear:  # If paper_idsandtitle is not empty
            for pidty in paper_idsandtitleandyear:
                paper_id=pidty[0]
                title=pidty[1]
                year=pidty[2]
                flattened_data.append([name, text, yearoforiginal, keyword, paper_id, title,year])
        else:  # If paper_idsandtitle is empty
            flattened_data.append([name, text, yearoforiginal, keyword, '','', ''])  # Empty cell for paper_id and title


    columns=['Title of original reference article', 'Text in main article referencing reference article', 'Year reference article released', 'Keywords for graph paper search','Paper Id of new reference article found', 'Title of new reference article found','Year new reference article found published']
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

