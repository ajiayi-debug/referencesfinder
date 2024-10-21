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
import time
from gpt_rag_asyncio import *
import asyncio
import aiohttp
from tqdm.asyncio import tqdm_asyncio
from crossref import *
import ast
import re

load_dotenv()
#main pdf
pdf_to_check = os.getenv("PDF")
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']

loop = asyncio.get_event_loop()







async def process_row_async(row, code):
    """Async function to process each row in the DataFrame using the async Azure OpenAI call."""
    chunk = row['Text Content']
    ref = code[0]
    
    # Use the async wrapper to call the GPT service with retry logic
    ans = await call_retrieve_sieve_with_async(chunk, ref)


    
    # Create a new row regardless of the answer
    new_row = pd.DataFrame({
        'Reference article name': [code[1]],
        'Reference text in main article': [code[0]],
        'Sieving by gpt 4o': [ans],
        'Chunk': [chunk],
        'Date': [code[2]]
    })
    
    # Determine which category the result falls into
    if ans not in ["'no'", "'no.'", "'"+ref.lower()+"'", "no", "no.", '']:
        return 'valid', new_row
    else:
        return 'no', new_row


async def retrieve_sieve_async(df, code):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    valid_dfs = []
    non_valid_dfs = []  # Initialize the non-valid list
    no_dfs = []

    # Process each row asynchronously using the process_row_async function
    tasks = [process_row_async(row, code) for _, row in df.iterrows()]
    
    # Use tqdm_asyncio to track progress of async tasks
    for result_type, new_row in await tqdm_asyncio.gather(*tasks, desc='Processing rows in parallel'):
        if result_type == 'valid':
            valid_dfs.append(new_row)
        elif result_type == 'no':
            no_dfs.append(new_row)
        else:
            non_valid_dfs.append(new_row)  # Collect non-valid rows if the result is not 'valid' or 'no'
    
    # Concatenate valid rows
    valid_output_df = pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()

    # Concatenate non-valid rows if no valid chunks found
    non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True) if non_valid_dfs else pd.DataFrame()

    # Concatenate no rows
    no_df = pd.concat(no_dfs, ignore_index=True) if no_dfs else pd.DataFrame()

    return valid_output_df, non_valid_output_df, no_df


def retrieve_sieve(df, code):
    """Synchronous wrapper function for calling async operations."""
    global loop

    # Check if the event loop is already running
    if loop.is_running():
        # Use asyncio.run_coroutine_threadsafe to submit async work to the existing loop
        return asyncio.run_coroutine_threadsafe(retrieve_sieve_async(df, code), loop).result()
    else:
        # Otherwise, create and run a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(retrieve_sieve_async(df, code))

def retrieve_sieve_references(collection_processed_name, valid_collection_name, invalid_collection_name):
    output_directory = 'RAG'  # Fixed output directory
    
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
    codable_collection=db['collated_statements_and_citations']
    codable_df = list(
    codable_collection.find(
                {},  # No filter, retrieve all documents
                {
                    '_id': 1,
                    'Reference article name': 1,
                    'Reference text in main article': 1,
                    'Date': 1,
                    'Name of authors': 1
                }
            )
        )
    codable_df = pd.DataFrame(codable_df, columns=[ 'Reference text in main article', 'Reference article name','Date', 'Name of authors'])
    
    codable=codable_df.values.tolist()
    # Perform full cycle and get references
    # text = full_cycle(pdf_to_check, filename="extracted")
    # output = get_references(text)
    # codable = ast.literal_eval(output)
    #Check if any paper retracted or corrected. If yes, send to user as an excel file for user to take note (either way we are going to look for more recent papers) and send to mongo db 
    #for us to edit in final paper if the paper cannot be updated (like its the same paper in the final form)
    unique_dict = {item[1]: item for item in codable}
    unique_list = list(unique_dict.values())
    df_extract_retract=df_check(unique_list)
    
    valid_dfs = []
    non_valid_dfs = []
    not_dfs=[]
    for code in tqdm(codable, desc="Retrieving and Sieving with an agent"):
        # Retrieve the corresponding PDF for the code
        pdf = retrieve_pdf(df, code)
        if pdf.empty:
            print(f"No PDF found for code: {code}")
            continue

        # Call the wrapper function to retrieve and sieve
        valid, non_valid, no_df = retrieve_sieve(pdf, code)
        
        # Append the results to the corresponding lists
        if not valid.empty:
            valid_dfs.append(valid)
        if not non_valid.empty:
            non_valid_dfs.append(non_valid)
        if not no_df.empty:
            not_dfs.append(no_df)
        

    # Concatenate non-valid results
    if non_valid_dfs:
        non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
        non_valid=invalid_collection_name+'.xlsx'
        send_excel(non_valid_output_df, 'RAG', non_valid)
        records = non_valid_output_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, invalid_collection_name, records)
    if not_dfs:
        not_df=pd.concat(not_dfs, ignore_index=True)
        send_excel(not_df, 'RAG', 'gpt_retrieve_sieve_rejected.xlsx')
    # Send valid results to MongoDB
    if valid_dfs:
        valid_output_df = pd.concat(valid_dfs, ignore_index=True)
        valid=valid_collection_name+'.xlsx'
        send_excel(valid_output_df, 'RAG', valid)

        # Convert to records and send to MongoDB
        records = valid_output_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, valid_collection_name, records)
        

    print("Process completed and data sent to MongoDB.")


def retrieve_sieve_references_new(collection_processed_name, new_ref_collection, valid_collection_name, invalid_collection_name, not_match):
    output_directory = 'RAG'  # Fixed output directory
    
    # Get collections from MongoDB
    collection_processed = db[collection_processed_name]
    collection_f=db[new_ref_collection]
    # Fetch documents from MongoDB
    documents1 = list(collection_processed.find({}, {'_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks': 1}))
    df = pd.DataFrame(documents1)

    documents2=list(collection_f.find({},{'_id': 1, 'Title of original reference article': 1, 'Text in main article referencing reference article': 1, 'Year reference article released': 1, 'Keywords for graph paper search': 1, 'Paper Id of new reference article found': 1, 'Title of new reference article found': 1, 'Year new reference article found published': 1, 'downloadable': 1, 'externalId_of_undownloadable_paper': 1, 'reason_for_failure': 1, 'pdf_url':1}))

    df_found=pd.DataFrame(documents2)
    df=replace_pdf_file_with_title(df, df_found)
    df_found=update_downloadable_status_invalid(df_found)
    df_found = df_found[df_found['downloadable'] != 'no']
    df_found = df_found[df_found['Paper id'] != '']
    

    codable=[]
    for index, row in df_found.iterrows():
        text=row['Text in main article referencing reference article']
        title=row['Title of new reference article found']
        year=row['Year new reference article found published']
        codable.append([text,title,year])

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
        

    # Concatenate non-valid results
    if non_valid_dfs:
        non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
        non_valid=invalid_collection_name+'.xlsx'
        send_excel(non_valid_output_df, 'RAG', non_valid)
        records = non_valid_output_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, invalid_collection_name, records)
    if not_dfs:
        not_df=pd.concat(not_dfs, ignore_index=True)
        reject=not_match+'.xlsx'
        send_excel(not_df, 'RAG', reject)
        records = not_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, not_match, records)
        
    # Send valid results to MongoDB
    if valid_dfs:
        valid_output_df = pd.concat(valid_dfs, ignore_index=True)
        valid=valid_collection_name+'.xlsx'
        send_excel(valid_output_df, 'RAG', valid)

        # Convert to records and send to MongoDB
        records = valid_output_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, valid_collection_name, records)
        

    print("Process completed and data sent to MongoDB.")



#re-ranking functions
def group_data_by_reference(df):
    """Group DataFrame rows by Reference article name and text, converting each group into a list of lists."""
    grouped = df.groupby(['Reference article name', 'Reference text in main article'])

    # Convert each group to a list of lists (one list per row)
    grouped_lists = {
        key: group[['Chunk', 'Sieving by gpt 4o', 'Date']].values.tolist()
        for key, group in grouped
    }
    return grouped_lists
