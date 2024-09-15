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
import ast

collection = 'subdocument_retrieved'
extraction = 'main_paper_extracts'
collections='subdocument_cossim'
database='data'

def main():
    # Get MongoDB URI from environment variables
    uri = os.getenv("uri_mongo")
    client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
    db = client['data']
    
    # Get collections from MongoDB
    collection_embed = db[collection]
    extract = db[extraction]

    # Fetch documents from MongoDB
    documents = list(collection_embed.find({}, {'_id': 1, 'PDF File': 1, 'Text Content': 1, 'Subdocument': 1, 'Summary':1,'normalized_pdf_file': 1, 'Reference':1,'Contains Reference': 1, 'Text Chunks': 1}))
    main_doc = list(extract.find({}, {'_id': 0, 'Reference': 1, 'Article Name': 1, 'Year': 1}))  # Exclude '_id' from 'extract' collection
    
    # Convert MongoDB documents to DataFrame
    codable = pd.DataFrame(main_doc)  # 'codable' will not have '_id' column
    codable = codable.values.tolist() 
    
    
    df = pd.DataFrame(documents)
    df['_id'] = df['_id'].astype(str)  # Ensure ObjectId is converted to string
    
    # Process data
    split_df = splitting(df, 'Text Chunks')
    token_df = tokenize(split_df, 'Text Chunks')
    chunki = chunking(token_df, 'Text Chunks', 8190)
    emb = embed(chunki)
    
    # Initialize list to store DataFrames
    dfs = []
    # Iterate over 'codable' with progress bar
    for code in tqdm(codable, desc='Calculating cosine similarity for each reference with selected subdocument'):
        # Calculate cosine similarity
        similar = retrieve_similar_text_threshold(emb, code, 10, 0.5)
        temp_dfs = []
        for index, row in similar.iterrows():
            textchunk = row['Text Chunks']
            cossim = row['similarities_text']
            subdoc=row['Subdocument']
            summary=row['Summary']
            newrow = pd.DataFrame({
                    'reference article name': [code[1]], 
                    'Reference text in main article': [code[0]],  
                    'Chunk': [textchunk], 
                    'Subdocument': [subdoc],
                    'Summary': [summary],
                    'Cosine Similarity': [cossim],
                    'Date': [code[2]]
                })
            temp_dfs.append(newrow)
        if temp_dfs:
            combined_temp_dfs = pd.concat(temp_dfs, ignore_index=True)
            #top_rows = combined_temp_dfs.head(3)
            dfs.append(combined_temp_dfs)
    
    # Combine all DataFrames
    output_df = pd.concat(dfs, ignore_index=True)
    
    # Send the DataFrame to Excel
    send_excel(output_df, 'RAG', 'subdocument_cossim.xlsx')

    records = output_df.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")

    # Send all records at once for collection
    replace_database_collection(uri, database, collections, records)
    print(f"Data sent to MongoDB Atlas for collection: {collections}")

    

if __name__ == "__main__":
    # This block will only execute if the script is run directly
    main()