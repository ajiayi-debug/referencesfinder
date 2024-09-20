from gpt_rag import *
from pdf import *
from embedding import *
import ast
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from call_mongodb import *
from tqdm import tqdm
import certifi

load_dotenv()
#main pdf
pdf_to_check = os.getenv("PDF")
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']

def retrieve(df,code):
    ref=code[0]
    dfs=[]
    for row,index in df.iterrows():
        chunk=row['Text Content']
        ans=retriever(chunk,ref)

        newrow = pd.DataFrame({
                'reference article name': [code[1]], 
                'Reference text in main article': [code[0]], 
                'Retrieval by gpt 4o':[ans],
                'Chunk': [chunk], 
                'Date': [code[2]]
            })
        dfs.append(newrow)
    output_df = pd.concat(dfs, ignore_index=True)
    return output_df


def sieve(df, code):
    ref=code[0]
    dfs=[]
    for row,index in df.iterrows():
        chunk=row['Chunk']
        ans=row['Retrieval by gpt 4o']
        sieve=siever(chunk,ref)
        newrow = pd.DataFrame({
                'reference article name': [code[1]], 
                'Reference text in main article': [code[0]], 
                'Retrieval by gpt 4o':[ans],
                'Sieving by gpt 4o':[sieve],
                'Chunk': [chunk], 
                'Date': [code[2]]
            })
        dfs.append(newrow)
    output_df = pd.concat(dfs, ignore_index=True)
    return output_df



def process_nonembed_references(collection_processed_name, collection_name):
    output_directory = 'RAG'  # Fixed output directory
    pdf_to_check = os.getenv("PDF")
    
    # Get collections from MongoDB
    collection_processed = db[collection_processed_name]

    # Fetch documents from MongoDB
    documents = list(collection_processed.find({}, {
        '_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks': 1, 'embed_v3': 1
    }))
    df = pd.DataFrame(documents)
    
    # Perform full cycle and get references
    text = full_cycle(pdf_to_check, filename="extracted")
    output = get_references(text)
    codable = ast.literal_eval(output)
    #[text from main article, name of reference article, year of reference article]

    dfs = []
    for code in tqdm(codable, desc="Processing cosine similarity, re-ranking and pruning"):
        pdf = retrieve_pdf(df, code)
        retrieved=retrieve(pdf,code)
        sieved=sieve(retrieved,code)
        dfs.append(sieved)
    output_df=pd.concat(dfs,ignore_index=True)
    send_excel(output_df,'RAG','gpt_retrieve_sieve.xlsx')
    records = output_df.to_dict(orient='records')
    replace_database_collection(uri, db.name, collection_name, records)

    print("Data sent to MongoDB Atlas.")



