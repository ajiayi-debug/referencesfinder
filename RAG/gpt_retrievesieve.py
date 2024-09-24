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

def retrieve_sieve(df, code):
    ref = code[0]
    valid_dfs = []
    non_valid_dfs = []
    no_dfs = []
    
    # Iterate through the dataframe rows
    for index, row in tqdm(df.iterrows(), desc='Retrieving chunks then sieving using GPT-4o as an agent'):
        chunk = row['Text Content']
        ans = retriever_and_siever(chunk, ref)
        if ans is not None:
            ans=ans.lower()

        # Create a new row regardless of the answer
        newrow = pd.DataFrame({
            'Reference article name': [code[1]], 
            'Reference text in main article': [code[0]], 
            'Sieving by gpt 4o': [ans],
            'Chunk': [chunk], 
            'Date': [code[2]]
        })
        # Append to appropriate list based on the answer
        if ans.lower() not in ["'no'", "'no.'", "'"+ref.lower()+"'","no","no."]:
            valid_dfs.append(newrow)
        else:
            no_dfs.append(newrow)
    
    # Concatenate valid rows
    valid_output_df = pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()
    print(valid_output_df['Sieving by gpt 4o'])
    # Concatenate non-valid rows if no valid chunks found
    if not valid_dfs and df.empty:
        non_valid_row = pd.DataFrame({
            'Reference article name': [code[1]], 
            'Reference text in main article': [code[0]], 
            'Date': [code[2]]
        })
        non_valid_dfs.append(non_valid_row)
    
    non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True) if non_valid_dfs else pd.DataFrame()
    
    # Concatenate no rows
    no_df = pd.concat(no_dfs, ignore_index=True) if no_dfs else pd.DataFrame()

    return valid_output_df, non_valid_output_df, no_df


def retrieve_sieve_references(collection_processed_name, collection_name):
    output_directory = 'RAG'  # Fixed output directory
    pdf_to_check = os.getenv("PDF")
    
    # Get collections from MongoDB
    collection_processed = db[collection_processed_name]

    # Fetch documents from MongoDB
    documents = list(collection_processed.find({}, {
        '_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks': 1
    }))
    
    if not documents:
        print("No documents found in MongoDB.")
        return
    
    df = pd.DataFrame(documents)
    
    # Perform full cycle and get references
    text = full_cycle(pdf_to_check, filename="extracted")
    output = get_references(text)
    codable = ast.literal_eval(output)

    valid_dfs = []
    non_valid_dfs = []
    not_dfs=[]
    for code in tqdm(codable, desc="Retrieving and Sieving with an agent"):
        pdf = retrieve_pdf(df, code)
        if pdf.empty:
            print(f"No PDF found for code: {code}")
            continue

        # Retrieve and sieve
        valid, non_valid ,no_df= retrieve_sieve(pdf, code)

        if not valid.empty:
            valid_dfs.append(valid)
        if not non_valid.empty:
            non_valid_dfs.append(non_valid)
        if not no_df.empty:
            not_dfs.append(no_df)

    # Concatenate valid results
    if valid_dfs:
        valid_output_df = pd.concat(valid_dfs, ignore_index=True)
        send_excel(valid_output_df, 'RAG', 'gpt_retrieve_sieve_valid_test8.xlsx')

    # Concatenate non-valid results
    if non_valid_dfs:
        non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
        send_excel(non_valid_output_df, 'RAG', 'gpt_retrieve_sieve_non_valid_test8.xlsx')
    if not_dfs:
        not_df=pd.concat(not_dfs, ignore_index=True)
        send_excel(not_df, 'RAG', 'gpt_retrieve_sieve_rejected_test8.xlsx')
    # Send valid results to MongoDB
    if valid_dfs:
        records = valid_output_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, collection_name, records)

    print("Process completed and data sent to MongoDB.")