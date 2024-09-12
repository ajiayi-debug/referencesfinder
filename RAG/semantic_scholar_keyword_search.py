from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from gpt_rag import *
from pdf import *
from gpt_rag import *
from embedding import *
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



def search_and_retrieve_keyword(collection_name, collection1_name):
    collection=db[collection_name]
    collection1=collection1_name
    documents = list(collection.find({}, {'_id': 1, 'reference article name': 1, 'Reference text in main article': 1, 'Reference identified by gpt4o in chunk': 1, 'Chunk': 1, 'Date': 1 }))
    df = pd.DataFrame(documents)
    nametextdate=[]
    field = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess'
    for index, row in tqdm(df.iterrows(), desc="Processing DataFrame rows", total=len(df)):
        name=row['reference article name']
        text=row['Reference text in main article']
        date=row['Date']
        if [name,text,date] not in nametextdate:
            nametextdate.append([name,text,date])
    download=[]
    ext_id=[]
    for ntd in tqdm(nametextdate, desc="Processing references"):
        n=ntd[0]
        t=ntd[1]
        d=ntd[2]
        keyword=keyword_search(t)
        ntd.append(keyword)
        papers = total_search_by_keywords(keyword, year=d, exclude_name=n, fields=field)
        external_id_list, filtered_metadata_list = preprocess_paper_metadata(papers)
        for data in filtered_metadata_list:
            download.append(data)
        total=papers
        # print(total)
        paper_ids=extract_paper_ids(total)
        title=extract_title(total)
        year=extract_year(total)
        paperidandtitleandyear=[]
        for k in range(len(paper_ids)):
            paperidandtitleandyear.append([paper_ids[k],title[k],year[k]])
        ntd.append(paperidandtitleandyear)
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

