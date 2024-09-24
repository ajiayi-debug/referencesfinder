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

def retrieve(df, code):
    ref = code[0]
    valid_dfs = []
    non_valid_dfs = []
    
    for index, row in tqdm(df.iterrows(), desc='Retrieving chunks using gpt 4o as an agent'):
        chunk = row['Text Content']
        ans = retriever(chunk, ref)
        if ans is not None:
            ans = ans.lower()

        # Only append the row if ans is "yes"
        if ans == "yes":
            newrow = pd.DataFrame({
                'Reference article name': [code[1]], 
                'Reference text in main article': [code[0]], 
                'Retrieval by gpt 4o': [ans],
                'Chunk': [chunk], 
                'Date': [code[2]]
            })
            valid_dfs.append(newrow)
    
    # Concatenate valid rows if there are any
    if valid_dfs:
        valid_output_df = pd.concat(valid_dfs, ignore_index=True)
    else:
        # If no valid rows (i.e., not a single "yes" in ans), append a single row to non_valid_dfs
        non_valid_row = pd.DataFrame({
            'Reference article name': [code[1]], 
            'Reference text in main article': [code[0]], 
            'Date': [code[2]]
        })
        non_valid_dfs.append(non_valid_row)
        valid_output_df = pd.DataFrame()  # No valid rows, so return an empty valid_output_df
    
    # Concatenate non-valid rows (if any)
    if non_valid_dfs:
        non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
    else:
        non_valid_output_df = pd.DataFrame()  # Return empty dataframe if no non-valid rows

    return valid_output_df, non_valid_output_df


def sieve(df, code):
    ref = code[0]
    valid_dfs = []

    for index, row in tqdm(df.iterrows(), desc='Sieving chunks using gpt 4o'):
        chunk = row['Chunk']
        ans = row['Retrieval by gpt 4o']
        sieve = siever(chunk, ref)

        # Only append the row if sieving is valid
        if sieve:  # You can define more specific validity checks here
            newrow = pd.DataFrame({
                'Reference article name': [code[1]], 
                'Reference text in main article': [code[0]], 
                'Retrieval by gpt 4o': [ans],
                'Sieving by gpt 4o': [sieve],
                'Chunk': [chunk], 
                'Date': [code[2]]
            })
            valid_dfs.append(newrow)

    # Concatenate valid rows
    if valid_dfs:
        valid_output_df = pd.concat(valid_dfs, ignore_index=True)
    else:
        valid_output_df = pd.DataFrame()  # Return empty dataframe if no valid rows

    return valid_output_df

def check(df):
    # Collect indices to drop
    indices_to_drop = []
    
    for index, row in tqdm(df.iterrows(), desc='Double checking if chunks actually support reference'):
        sieving_value = str(row['Sieving by gpt 4o']).lower()
        reference_value = str(row['Reference text in main article']).lower()

        if sieving_value in ['no', 'no.'] or sieving_value == reference_value:
            indices_to_drop.append(index)
    
    # Drop the rows after iterating
    df.drop(indices_to_drop, inplace=True)
    
    return df

def retrieve_then_sieve_references(collection_processed_name, collection_name):
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

    for code in tqdm(codable, desc="Retrieving and Sieving with an agent"):
        pdf = retrieve_pdf(df, code)
        if pdf.empty:
            print(f"No PDF found for code: {code}")
            continue

        # Retrieve and sieve
        retrieved_valid, retrieved_non_valid = retrieve(pdf, code)
        sieved= sieve(retrieved_valid, code)

        if not retrieved_valid.empty:
            valid_dfs.append(sieved)
        if not retrieved_non_valid.empty:
            non_valid_dfs.append(retrieved_non_valid)

    # Concatenate valid results
    if valid_dfs:
        valid_output_df = pd.concat(valid_dfs, ignore_index=True)
        valid_output_df=check(valid_output_df)
        send_excel(valid_output_df, 'RAG', 'gpt_retrieve_sieve_valid_test6.xlsx')

    # Concatenate non-valid results
    if non_valid_dfs:
        non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
        send_excel(non_valid_output_df, 'RAG', 'gpt_retrieve_sieve_non_valid_test6.xlsx')

    # Send valid results to MongoDB
    if valid_dfs:
        records = valid_output_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, collection_name, records)

    print("Process completed and data sent to MongoDB.")