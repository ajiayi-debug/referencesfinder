import os
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm
from .pdf import *
from .gpt_rag import *
from .embedding import *
from .call_mongodb import *
from .semantic_chunking import *
from .mongo_client import MongoDBClient
load_dotenv()
client = MongoDBClient.get_client()
db = client['data']
uri = os.getenv("uri_mongo")



def process_pdfs_to_mongodb(files_directory, collection1, collection2):
    
    directory = 'doc'  # Fixed directory

    pdf_list = read_pdf_file_list(files_directory)
    
    # Process and save PDFs
    process_and_save_pdfs(pdf_list, directory)
    filenames = get_txt_names(files_directory)

    processed_texts = read_processed_texts(directory, filenames)
    processed_name = get_names(filenames, directory)
    

    data = {'PDF File': processed_name, 'Text Content': processed_texts}
    df = pd.DataFrame(data)
    tqdm.pandas(desc="Processing Documents for Chunking")
    df['text_chunks'] = df['Text Content'].apply(semantic_chunk)
    
    df_exploded = df.explode('text_chunks').drop(columns=['Text Content'])
    
    # Rename the columns for clarity
    df_exploded.rename(columns={'text_chunks': 'Text Content'}, inplace=True)

    # Embed
    split_df = splitting(df_exploded, 'Text Content')
    token_df = tokenize(split_df, 'Text Content')
    chunki = chunking(token_df, 'Text Content', 8190)

    emb=embed(chunki)

    # Convert DataFrames to records
    records1 = df_exploded.to_dict(orient='records')
    records2 = emb.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")

    # Send all records at once for collection1
    replace_database_collection(uri, db.name, collection1, records1)
    print(f"Data sent to MongoDB Atlas for collection: {collection1}")

    # Send all records at once for collection2
    replace_database_collection(uri, db.name, collection2, records2)
    print(f"Data sent to MongoDB Atlas for collection: {collection2}")

    delete_folder(directory)

def process_new_pdfs_to_mongodb(files_directory, collection1, collection2):
    
    directory = 'doc'  # Fixed directory

    pdf_list = read_pdf_file_list(files_directory)
    #filenames = get_txt_names(files_directory)
    
    # Process and save PDFs
    process_invalid_pdfs(pdf_list)
    pdf_list = read_pdf_file_list(files_directory)
    #print(pdf_list)
    process_and_save_pdfs(pdf_list, directory)
    filenames= get_txt_names(files_directory)


    processed_texts = read_processed_texts(directory, filenames)
    #processed_name = get_names(filenames, directory)
    processed_name=list_pdf_bases('papers')
    
    

    data = {'PDF File': processed_name, 'Text Content': processed_texts}
    df = pd.DataFrame(data)
    tqdm.pandas(desc="Processing Documents for Chunking")
    df['text_chunks'] = df['Text Content'].apply(semantic_chunk)
    
    df_exploded = df.explode('text_chunks').drop(columns=['Text Content'])
    
    # Rename the columns for clarity
    df_exploded.rename(columns={'text_chunks': 'Text Content'}, inplace=True)

    # Embed
    split_df = splitting(df_exploded, 'Text Content')
    token_df = tokenize(split_df, 'Text Content')
    chunki = chunking(token_df, 'Text Content', 8190)

    emb=embed(chunki)

    # Convert DataFrames to records
    records1 = df_exploded.to_dict(orient='records')
    records2 = emb.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")

    # Send all records at once for collection1
    replace_database_collection(uri, db.name, collection1, records1)
    print(f"Data sent to MongoDB Atlas for collection: {collection1}")

    # Send all records at once for collection2
    replace_database_collection(uri, db.name, collection2, records2)
    print(f"Data sent to MongoDB Atlas for collection: {collection2}")

    delete_folder(directory)

def process_pdfs_to_mongodb_noembed(files_directory, collection1):
    #Note no embed means embedding not used for retrieval but embedding is used to calculate chunking boundary!!!
    
    directory = 'doc'  # Fixed directory
    delete_folder(directory)
    pdf_list = read_pdf_file_list(files_directory)
    
    # Process and save PDFs
    process_and_save_pdfs(pdf_list, directory)
    filenames = get_txt_names(files_directory)

    processed_texts = read_processed_texts(directory, filenames)
    processed_name = get_names(filenames, directory)
    

    data = {'PDF File': processed_name, 'Text Content': processed_texts}
    df = pd.DataFrame(data)
    df=process_dataframe_sc1(df)

    #df = process_dataframe_into_chunks(df)
    
    df_exploded = df.explode('text_chunks').drop(columns=['Text Content'])
    
    # Rename the columns for clarity
    df_exploded.rename(columns={'text_chunks': 'Text Content'}, inplace=True)


    # Convert DataFrames to records
    records1 = df_exploded.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")

    # Send all records at once for collection1
    replace_database_collection(uri, db.name, collection1, records1)
    print(f"Data sent to MongoDB Atlas for collection: {collection1}")


    delete_folder(directory)


def process_pdfs_to_mongodb_noembed_new(files_directory, collection1, change_to_add=False):
    directory = 'doc'  # Fixed directory
    delete_folder(directory)
    pdf_list = read_pdf_file_list(files_directory)
    #filenames = get_txt_names(files_directory)
    
    # Process and save PDFs
    process_invalid_pdfs(pdf_list)
    pdf_list = read_pdf_file_list(files_directory)
    #print(pdf_list)
    process_and_save_pdfs(pdf_list, directory)
    filenames= get_txt_names(files_directory)


    processed_texts = read_processed_texts(directory, filenames)
    #processed_name = get_names(filenames, directory)
    processed_name=list_pdf_bases(files_directory)
    
    

    data = {'PDF File': processed_name, 'Text Content': processed_texts}
    df = pd.DataFrame(data)
    df=process_dataframe_sc1(df)

    #df = process_dataframe_into_chunks(df)
    
    df_exploded = df.explode('text_chunks').drop(columns=['Text Content'])
    
    # Rename the columns for clarity
    df_exploded.rename(columns={'text_chunks': 'Text Content'}, inplace=True)

    
    # Convert DataFrames to records
    records1 = df_exploded.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")

    # Send all records at once for collection1
    if change_to_add:
        insert_documents(uri,db.name,collection1,records1)
    else:
        replace_database_collection(uri, db.name, collection1, records1)

    print(f"Data sent to MongoDB Atlas for collection: {collection1}")


    delete_folder(directory)