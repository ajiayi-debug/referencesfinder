import os
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm
from pdf import *
from gpt_rag import *
from embedding import *
from call_mongodb import *
from semantic_chunking import *

def process_new_pdfs_to_mongodb(files_directory, collection1, collection2):
    load_dotenv()
    uri = os.getenv("uri_mongo")
    client = MongoClient(uri)
    db = 'data'
    
    directory = 'doc'  # Fixed directory

    pdf_list = read_pdf_file_list(files_directory)
    # filenames = get_txt_names(files_directory)
    
    # Process and save PDFs
    process_and_save_pdfs(pdf_list, directory)
    filenames= get_txt_names(files_directory)
    

    processed_texts = read_processed_texts(directory, filenames)
    #processed_name = get_names(filenames, directory)
    processed_name=list_pdf_bases('papers')
    print(processed_name)
    

    data = {'PDF File': processed_name, 'Text Content': processed_texts}
    df = pd.DataFrame(data)
   
    df['text_chunks'] = df['Text Content'].apply(semantic_chunk)
    
    df_exploded = df.explode('text_chunks').drop(columns=['Text Content'])
    
    # Rename the columns for clarity
    df_exploded.rename(columns={'text_chunks': 'Text Content'}, inplace=True)

    # Embed
    split_df = splitting(df_exploded, 'Text Content')
    token_df = tokenize(split_df, 'Text Content')
    chunki = chunking(token_df, 'Text Content', 8190)

    emb=embed(chunki)
    final_ans='new_ref_emb.xlsx'
    send_excel(emb,'RAG', final_ans)

    # Convert DataFrames to records
    records1 = df_exploded.to_dict(orient='records')
    records2 = emb.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")

    # Send all records at once for collection1
    replace_database_collection(uri, db, collection1, records1)
    print(f"Data sent to MongoDB Atlas for collection: {collection1}")

    # Send all records at once for collection2
    replace_database_collection(uri, db, collection2, records2)
    print(f"Data sent to MongoDB Atlas for collection: {collection2}")

    clear_folder(directory)