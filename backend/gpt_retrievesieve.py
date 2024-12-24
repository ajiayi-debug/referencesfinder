from .gpt_rag import *
from .pdf import *
import ast
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from .call_mongodb import *
from tqdm import tqdm
import certifi
import time
from .gpt_rag_asyncio import *
import asyncio
import aiohttp
from tqdm.asyncio import tqdm_asyncio
from .crossref import *
import ast
import re
from rapidfuzz import fuzz
from .mongo_client import MongoDBClient

load_dotenv()
client = MongoDBClient.get_client()
db = client['data']



async def process_row_async(row, code):
    """Async function to process each row in the DataFrame using the async Azure OpenAI call."""
    chunk = row['Text Content']
    ref = code[0]
    
    await asyncio.sleep(10)
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
    if ans not in ["'no'", "'no.'", "'"+ref.lower()+"'", "no", "no.", '', None]:
        return 'valid', new_row
    else:
        return 'no', new_row
    
#deprecieted: classification for existing reference is important as well
# async def process_row_async_check(row, code):
#     """Async function to process each row in the DataFrame using the async Azure OpenAI call."""
#     chunk = row['Text Content']
#     ref = code[0]
    

#     await asyncio.sleep(10)
#     # Use the async wrapper to call the GPT service with retry logic
#     ans = await call_retrieve_sieve_with_async_check(chunk, ref)


    
#     # Create a new row regardless of the answer
#     new_row = pd.DataFrame({
#         'Reference article name': [code[1]],
#         'Reference text in main article': [code[0]],
#         'Sieving by gpt 4o': [ans],
#         'Chunk': [chunk],
#         'Date': [code[2]]
#     })
    
#     # Determine which category the result falls into
#     if ans not in ["'no'", "'no.'", "'"+ref.lower()+"'", "no", "no.", '', None]:
#         return 'valid', new_row
#     else:
#         return 'no', new_row


async def retrieve_sieve_async(df, code):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    valid_dfs = []
    non_valid_dfs = []  # Initialize the non-valid list
    no_dfs = []

    # Process each row asynchronously using the process_row_async function
    # Define a semaphore to limit the number of concurrent tasks (added because VPN cause my tasks to throttle, you can try to remove from this line onwards to)
    semaphore = asyncio.Semaphore(20)  # Adjust the number as needed

    async def process_row_with_semaphore(row):
        """Wrapper function to use semaphore for each task."""
        async with semaphore:
            return await process_row_async(row, code)
    # Create tasks with semaphore-wrapped function
    tasks = [process_row_with_semaphore(row) for _, row in df.iterrows()]
    #this line then replace with
    #tasks = [process_row_async(row) for _, row in df.iterrows()]
    #for quicker times (for context, without the vpn a 8 hours task takes 2 hours)
    
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


async def retrieve_sieve_async_check(df, code):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    valid_dfs = []
    non_valid_dfs = []  # Initialize the non-valid list
    no_dfs = []

    # Process each row asynchronously using the process_row_async function
    # Define a semaphore to limit the number of concurrent tasks (added because VPN cause my tasks to throttle, you can try to remove from this line onwards to)
    semaphore = asyncio.Semaphore(20)  # Adjust the number as needed

    async def process_row_with_semaphore(row):
        """Wrapper function to use semaphore for each task."""
        async with semaphore:
            return await process_row_async(row, code)
    # Create tasks with semaphore-wrapped function
    tasks = [process_row_with_semaphore(row) for _, row in df.iterrows()]
    #this line then replace with
    #tasks = [process_row_async(row) for _, row in df.iterrows()]
    #for quicker times (for context, without the vpn a 8 hours task takes 2 hours)
    
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
    try:
        return asyncio.run(retrieve_sieve_async(df, code))
    except Exception as e:
        print(f"An error occurred: {e}")
        # Handle exceptions or re-raise

def retrieve_sieve_check(df, code):
    """Synchronous wrapper function for calling async operations."""
    try:
        return asyncio.run(retrieve_sieve_async_check(df, code))
    except Exception as e:
        print(f"An error occurred: {e}")
        # Handle exceptions or re-raise



from tqdm import tqdm

# Sanity checking existing references
def retrieve_sieve_references(collection_processed_name, valid_collection_name, invalid_collection_name):
    try:
        output_directory = 'backend'  # Fixed output directory
        
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
        codable_collection = db['collated_statements_and_citations']
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
        codable_df = pd.DataFrame(codable_df, columns=[
            'Reference text in main article',
            'Reference article name',
            'Date',
            'Name of authors'
        ])
        
        codable = codable_df.values.tolist()
        
        # Remove duplicates and check retractions/corrections
        unique_dict = {item[1]: item for item in codable}
        unique_list = list(unique_dict.values())
        df_extract_retract = df_check(unique_list)
        
        valid_dfs = []
        non_valid_dfs = []
        not_dfs = []

        # Already using tqdm for the loop
        for code in tqdm(codable, desc="Retrieving and Sieving with an agent"):
            pdf = retrieve_pdf(df, code)
            if pdf.empty:
                print(f"No PDF found for code: {code}")
                continue

            # Retrieve and sieve
            valid, non_valid, no_df = retrieve_sieve_check(pdf, code)

            if not valid.empty:
                valid_dfs.append(valid)
            if not non_valid.empty:
                non_valid_dfs.append(non_valid)
            if not no_df.empty:
                not_dfs.append(no_df)

        # Concatenate non-valid results
        if non_valid_dfs:
            non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
            non_valid = invalid_collection_name + '.xlsx'
            records = non_valid_output_df.to_dict(orient='records')
            replace_database_collection(uri, db.name, invalid_collection_name, records)

        if not_dfs:
            not_df = pd.concat(not_dfs, ignore_index=True)

        # Send valid results to MongoDB
        if valid_dfs:
            valid_output_df = pd.concat(valid_dfs, ignore_index=True)
            valid = valid_collection_name + '.xlsx'
            records = valid_output_df.to_dict(orient='records')
            replace_database_collection(uri, db.name, valid_collection_name, records)

        print("Process completed and data sent to MongoDB.")

    finally:
        # Force clear any leftover tqdm instances
        tqdm._instances.clear()


# Checking new references
def retrieve_sieve_references_new(
    collection_processed_name,
    new_ref_collection,
    valid_collection_name,
    invalid_collection_name,
    not_match,
    change_to_add=False
):
    try:
        # Get collections from MongoDB
        collection_processed = db[collection_processed_name]
        collection_f = db[new_ref_collection]

        # Fetch documents from MongoDB
        documents1 = list(collection_processed.find({}, {
            '_id': 1,
            'PDF File': 1,
            'Text Content': 1,
            'n_tokens': 1,
            'Text Chunks': 1
        }))
        if not documents1:
            print(f"No documents found in '{collection_processed_name}'. Skipping further processing.")
            return  # Exit the function early

        df = pd.DataFrame(documents1)

        documents2 = list(collection_f.find({}, {
            '_id': 1,
            'Title of original reference article': 1,
            'Text in main article referencing reference article': 1,
            'Year reference article released': 1,
            'Keywords for graph paper search': 1,
            'Paper Id of new reference article found': 1,
            'Title of new reference article found': 1,
            'Year new reference article found published': 1,
            'authors': 1,
            'downloadable': 1,
            'externalId_of_undownloadable_paper': 1,
            'reason_for_failure': 1,
            'pdf_url': 1
        }))

        df_found = pd.DataFrame(documents2)
        df = replace_pdf_file_with_title(df, df_found)
        df_found = update_downloadable_status_invalid(df_found)
        df_found = df_found[df_found['downloadable'] != 'no']
        df_found = df_found[df_found['Paper Id of new reference article found'] != '']

        codable = []
        for index, row in df_found.iterrows():
            text = row['Text in main article referencing reference article']
            title = row['Title of new reference article found']
            year = row['Year new reference article found published']
            codable.append([text, title, year])

        valid_dfs = []
        non_valid_dfs = []
        not_dfs = []

        # Use tqdm for the loop
        for code in tqdm(codable, desc="Retrieving and Sieving with an agent"):
            pdf = retrieve_pdf(df, code)
            if pdf.empty:
                print(f"No PDF found for code: {code}")
                continue

            # Retrieve and sieve
            valid, non_valid, no_df = retrieve_sieve(pdf, code)

            if not valid.empty:
                valid_dfs.append(valid)
            if not non_valid.empty:
                non_valid_dfs.append(non_valid)
            if not no_df.empty:
                not_dfs.append(no_df)

        if change_to_add:
            # Insert logic
            if non_valid_dfs:
                non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
                non_valid = invalid_collection_name + '.xlsx'
                records = non_valid_output_df.to_dict(orient='records')
                insert_documents(uri, db.name, invalid_collection_name, records)

            if not_dfs:
                not_df = pd.concat(not_dfs, ignore_index=True)
                reject = not_match + '.xlsx'
                records = not_df.to_dict(orient='records')
                insert_documents(uri, db.name, not_match, records)

            if valid_dfs:
                valid_output_df = pd.concat(valid_dfs, ignore_index=True)
                valid = valid_collection_name + '.xlsx'
                records = valid_output_df.to_dict(orient='records')
                insert_documents(uri, db.name, valid_collection_name, records)
        else:
            # Replace logic
            if non_valid_dfs:
                non_valid_output_df = pd.concat(non_valid_dfs, ignore_index=True)
                non_valid = invalid_collection_name + '.xlsx'
                records = non_valid_output_df.to_dict(orient='records')
                replace_database_collection(uri, db.name, invalid_collection_name, records)

            if not_dfs:
                not_df = pd.concat(not_dfs, ignore_index=True)
                reject = not_match + '.xlsx'
                records = not_df.to_dict(orient='records')
                replace_database_collection(uri, db.name, not_match, records)

            if valid_dfs:
                valid_output_df = pd.concat(valid_dfs, ignore_index=True)
                valid = valid_collection_name + '.xlsx'
                records = valid_output_df.to_dict(orient='records')
                replace_database_collection(uri, db.name, valid_collection_name, records)

        print("Process completed and data sent to MongoDB.")
    
    finally:
        # Force clear any leftover tqdm instances
        tqdm._instances.clear()


# Function to extract valid classifications and scores
def extract_classification(text):
    if not isinstance(text, str) or not text.strip():
        return None  # Handle None or empty inputs

    # Improved regex to handle multiple spaces/newlines
    pattern = r"\s*(support|oppose)\s*\((\d+)\):\s*(.*?)\s*(?=\s*support|\s*oppose|\Z)"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

    if matches:
        # Create a DataFrame with each match as a separate row
        rows = [
            {
                'Sentiment': match[0], 
                'Confidence Score': int(match[1]), 
                'Sieving by gpt 4o': match[2].strip()
            }
            for match in matches
        ]
        return pd.DataFrame(rows)
    else:
        return None  # No valid matches found


def top_5_or_all_top_scores(group, threshold):
    """
    Returns all rows with the top score if more than 5 rows have the top score 
    and all scores are above the threshold. Otherwise, returns up to 5 rows 
    where all scores are above the threshold.
    """
    # Sort the group by 'Confidence Score' in descending order
    sorted_group = group.sort_values(by='Confidence Score', ascending=False)
    # Filter rows where 'Confidence Score' is above the threshold
    filtered_group = sorted_group[sorted_group['Confidence Score'] >= threshold]
    
    if filtered_group.empty:
        # If no rows meet the threshold, return an empty DataFrame
        return filtered_group
    
    # Get the top score from the filtered group
    top_score = filtered_group['Confidence Score'].iloc[0]
    # Check how many rows have the top score
    top_score_count = (filtered_group['Confidence Score'] == top_score).sum()
    
    if top_score_count > 5:
        # If more than 5 rows have the top score, return all rows with that top score
        return filtered_group[filtered_group['Confidence Score'] == top_score]
    else:
        # Otherwise, return all rows up to the top 5 that are above the threshold
        return filtered_group.head(5)

#get top score of each grp and check if below threshold

#check if that particular statement's new ref article none of chunks meet threshold OR all chunks are negative
def check_for_retry(group, threshold):
    # Check if all sentiments are negative
    all_negative_sentiment = (group['Sentiment'] == 'negative').all()

    # Check if the group contains positive sentiments
    has_positive_sentiment = (group['Sentiment'] == 'positive').any()

    # Initialize flag to decide whether to retry
    should_retry = False

    # Condition 1: For groups with positive sentiments, check if max score < threshold
    if has_positive_sentiment:
        # Filter positive sentiments within the group
        positive_group = group[group['Sentiment'] == 'positive']
        max_score = positive_group['Confidence Score'].max()
        if max_score < threshold:
            should_retry = True

    # Condition 2: If all sentiments are negative
    if all_negative_sentiment:
        should_retry = True

    if should_retry:
        return group
    else:
        return pd.DataFrame()





#to remove hallucination of model outputting the statement
def contains_reference_text(row):
    pattern = re.compile(re.escape(row['Reference text in main article']), re.IGNORECASE)
    return bool(pattern.search(row['Sieving by gpt 4o']))


def cleaning(valid_collection_name, not_match, top_5, threshold=75, change_to_add=False):
    # Fetch documents from the collection
    collection_valid = db[valid_collection_name]
    documents = list(
        collection_valid.find(
            {}, 
            {
                'Reference article name': 1, 
                'Reference text in main article': 1, 
                'Sieving by gpt 4o': 1, 
                'Chunk': 1, 
                'Date': 1
            }
        )
    )

    # Convert documents to a DataFrame
    df = pd.DataFrame(documents)
    print(df.columns)

    # Initialize lists for valid and invalid rows
    valid_rows = []
    invalid_rows = []

    

    # Iterate through rows and classify them
    for idx, row in df.iterrows():
        extracted_df = extract_classification(row['Sieving by gpt 4o'])

        if extracted_df is not None:
            # Add additional columns to the valid DataFrame
            extracted_df['Reference article name'] = row['Reference article name']
            extracted_df['Reference text in main article'] = row['Reference text in main article']
            extracted_df['Chunk'] = row['Chunk']
            extracted_df['Date'] = row['Date']
            valid_rows.append(extracted_df)
        else:
            # Store invalid rows if no valid classification is found
            invalid_rows.append(row)

    # Combine valid rows into a DataFrame
    valid_df = pd.concat(valid_rows, ignore_index=True) if valid_rows else pd.DataFrame()

    # If valid_df is empty, skip filtering and retry logic
    if valid_df.empty:
        print("No valid rows found. Skipping filtering and retry logic.")
        # Export invalid data if required
        invalid_df = pd.concat([pd.DataFrame(invalid_rows)], ignore_index=True)
        records3 = invalid_df.to_dict(orient='records')
        insert_documents(uri, db.name, not_match, records3)
        return  # Exit the function early as there's no valid data to process further

    # Identify rows where reference text is found within the content and remove them (hallucinations)
    matches_df = valid_df[valid_df.apply(contains_reference_text, axis=1)]
    filtered_df = valid_df[~valid_df.apply(contains_reference_text, axis=1)]

    # Apply the modified check_for_retry function without initial sentiment filtering
    retry_df = (
        filtered_df
        .groupby(
            ['Reference article name', 'Reference text in main article'], as_index=False
        )
        .apply(check_for_retry, threshold=threshold)
        .reset_index(drop=True)
    )

    # Remove rows belonging to retry_df from filtered_df to get the final valid_df
    if not retry_df.empty:
        common_columns = filtered_df.columns.intersection(retry_df.columns).tolist()
        valid_df = filtered_df.merge(
            retry_df[common_columns], 
            how='outer', 
            indicator=True
        ).query('_merge == "left_only"').drop('_merge', axis=1)
    else:
        valid_df = filtered_df.copy()

    # Group the remaining valid rows and apply the top 5 or all top scores logic
    top_ranked_with_ties_df = (
        valid_df.groupby(
            ['Reference article name', 'Reference text in main article', 'Sentiment'], as_index=False
        ).apply(top_5_or_all_top_scores, threshold=threshold).reset_index(drop=True)
    )

    if change_to_add:
        # Send top-ranked output to an Excel file
        xlsx = top_5 + '.xlsx'
        records1 = top_ranked_with_ties_df.to_dict(orient='records')
        upsert_database_and_collection(uri, db.name, top_5, records1)
        valid_xlsx = valid_collection_name + '.xlsx'
        records2 = valid_df.to_dict(orient='records')
        upsert_database_and_collection(uri, db.name, valid_collection_name, records2)
    else:
        # Send top-ranked output to an Excel file
        xlsx = top_5 + '.xlsx'
        records1 = top_ranked_with_ties_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, top_5, records1)
        valid_xlsx = valid_collection_name + '.xlsx'
        records2 = valid_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, valid_collection_name, records2)

    # Combine invalid rows and matches into one DataFrame
    invalid_df = pd.concat([pd.DataFrame(invalid_rows), matches_df], ignore_index=True)
    invalid_xlsx = not_match + '.xlsx'
    records3 = invalid_df.to_dict(orient='records')
    insert_documents(uri, db.name, not_match, records3)

    # If retry_df is not empty, save it
    if not retry_df.empty:
        records4 = retry_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, 'retry', records4)


def add_to_existing(collection_processed_name_new, collection_processed_name_original,
                    new_ref_collection_new, new_ref_collection_original,
                    valid_collection_name_new, valid_collection_name_original,
                    invalid_collection_name_new, invalid_collection_name_original,
                    not_match_new, not_match_original,
                    top_5_new,top_5_original):
    collection_processed = db[collection_processed_name_new]
    collection_f = db[new_ref_collection_new]
    collection_valid = db[valid_collection_name_new]
    collection_invalid = db[invalid_collection_name_new]
    collection_notmatch = db[not_match_new]
    collection_top5=db[top_5_new]
    
    # Fetch documents from MongoDB
    # Fetch documents from MongoDB
    documents1 = list(collection_processed.find({}, {
        '_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks': 1
    }))
    documents2 = list(collection_f.find({}, {
        '_id': 1,
        'Title of original reference article': 1,
        'Text in main article referencing reference article': 1,
        'Year reference article released': 1,
        'Keywords for graph paper search': 1,
        'Paper Id of new reference article found': 1,
        'Title of new reference article found': 1,
        'Year new reference article found published': 1,
        'authors':1,
        'downloadable': 1,
        'externalId_of_undownloadable_paper': 1,
        'reason_for_failure': 1,
        'pdf_url': 1
    }))
    documents3 = list(collection_valid.find({}, {
        '_id': 1,
        'Sentiment':1,
        'Confidence Score':1,
        'Sieving by gpt 4o': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Chunk': 1,
        'Date': 1
    }))
    documents4 = list(collection_invalid.find({}, {
        '_id': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Sieving by gpt 4o': 1,
        'Chunk': 1,
        'Date': 1
    }))
    documents5 = list(collection_notmatch.find({}, {
        '_id': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Sieving by gpt 4o': 1,
        'Chunk': 1,
        'Date': 1
    }))

    documents6 = list(collection_top5.find({}, {
        '_id': 1,
        'Sentiment':1,
        'Confidence Score':1,
        'Sieving by gpt 4o': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Chunk': 1,
        'Date': 1
    }))
    
    # Insert documents into the original collections then clear the new collection such that 
    # if there are no new data found in this iteration, the previous iteration of data will not be added due to 
    # it not being cleared in the previous iteration
    insert_documents(uri, db.name, collection_processed_name_original, documents1)
    clear_collection(uri, db.name, collection_processed_name_new)
    
    insert_documents(uri, db.name, new_ref_collection_original, documents2)
    clear_collection(uri, db.name, new_ref_collection_new)
    
    insert_documents(uri, db.name, valid_collection_name_original, documents3)
    clear_collection(uri, db.name, valid_collection_name_new)
    
    insert_documents(uri, db.name, invalid_collection_name_original, documents4)
    clear_collection(uri, db.name, invalid_collection_name_new)
    
    insert_documents(uri, db.name, not_match_original, documents5)
    clear_collection(uri, db.name, not_match_new)

    insert_documents(uri, db.name, top_5_original, documents6)
    clear_collection(uri, db.name, top_5_new)

#for easy debugging for developer side. Meant to send final collections to excel for viewing if you dont have mongo shell installed 
def send_excel_all(collection_processed_name,new_ref_collection,valid_collection_name,invalid_collection_name,not_match,top_5):
    
    # Fetch documents from MongoDB collections and convert to DataFrames
    df_processed = pd.DataFrame(list(db[collection_processed_name].find({}, {
        '_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks': 1
    })))
    name_processed=collection_processed_name+'.xlsx'
    send_excel(df_processed,'backend',name_processed)

    df_new_ref = pd.DataFrame(list(db[new_ref_collection].find({}, {
        '_id': 1,
        'Title of original reference article': 1,
        'Text in main article referencing reference article': 1,
        'Year reference article released': 1,
        'Keywords for graph paper search': 1,
        'Paper Id of new reference article found': 1,
        'Title of new reference article found': 1,
        'Year new reference article found published': 1,
        'authors':1,
        'downloadable': 1,
        'externalId_of_undownloadable_paper': 1,
        'reason_for_failure': 1,
        'pdf_url': 1
    })))
    name_new_ref=new_ref_collection + '.xlsx'
    send_excel(df_new_ref,'backend',name_new_ref)
    df_valid = pd.DataFrame(list(db[valid_collection_name].find({}, {
        '_id': 1,
        'Sentiment': 1,
        'Confidence Score': 1,
        'Sieving by gpt 4o': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Chunk': 1,
        'Date': 1
    })))
    name_valid=valid_collection_name+'.xlsx'
    send_excel(df_valid,'backend',name_valid)

    df_invalid = pd.DataFrame(list(db[invalid_collection_name].find({}, {
        '_id': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Sieving by gpt 4o': 1,
        'Chunk': 1,
        'Date': 1
    })))
    name_invalid=invalid_collection_name+'.xlsx'
    send_excel(df_invalid,'backend',name_invalid)

    df_not_match = pd.DataFrame(list(db[not_match].find({}, {
        '_id': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Sieving by gpt 4o': 1,
        'Chunk': 1,
        'Date': 1
    })))
    name_not_match=not_match +'.xlsx'
    send_excel(df_not_match,'backend',name_not_match)
    df_top_5 = pd.DataFrame(list(db[top_5].find({}, {
        '_id': 1,
        'Sentiment': 1,
        'Confidence Score': 1,
        'Sieving by gpt 4o': 1,
        'Reference article name': 1,
        'Reference text in main article': 1,
        'Chunk': 1,
        'Date': 1
    })))
    name_top_5=top_5+'.xlsx'
    send_excel(df_top_5,'backend',name_top_5)


#cleaning without retry logic since this is initial reference articles so we just     
def cleaning_initial(valid_collection_name, not_match, top_5, threshold=75, change_to_add=False):
    # Fetch documents from the collection
    collection_valid = db[valid_collection_name]
    documents = list(
        collection_valid.find(
            {}, 
            {
                'Reference article name': 1, 
                'Reference text in main article': 1, 
                'Sieving by gpt 4o': 1, 
                'Chunk': 1, 
                'Date': 1
            }
        )
    )

    # Convert documents to a DataFrame
    df = pd.DataFrame(documents)

    # Initialize lists for valid and invalid rows
    valid_rows = []
    invalid_rows = []

    

    # Iterate through rows and classify them
    for idx, row in df.iterrows():
        extracted_df = extract_classification(row['Sieving by gpt 4o'])

        if extracted_df is not None:
            # Add additional columns to the valid DataFrame
            extracted_df['Reference article name'] = row['Reference article name']
            extracted_df['Reference text in main article'] = row['Reference text in main article']
            extracted_df['Chunk'] = row['Chunk']
            extracted_df['Date'] = row['Date']
            valid_rows.append(extracted_df)
        else:
            # Store invalid rows if no valid classification is found
            invalid_rows.append(row)

    # Combine valid rows into a DataFrame
    valid_df = pd.concat(valid_rows, ignore_index=True) if valid_rows else pd.DataFrame()

    # If valid_df is empty, skip filtering and retry logic
    if valid_df.empty:
        print("No valid rows found. Skipping filtering and retry logic.")
        # Export invalid data if required
        invalid_df = pd.concat([pd.DataFrame(invalid_rows)], ignore_index=True)
        records3 = invalid_df.to_dict(orient='records')
        insert_documents(uri, db.name, not_match, records3)
        return  # Exit the function early as there's no valid data to process further

    # Identify rows where reference text is found within the content and remove them (hallucinations)
    matches_df = valid_df[valid_df.apply(contains_reference_text, axis=1)]
    filtered_df = valid_df[~valid_df.apply(contains_reference_text, axis=1)]

    

    # Group the valid rows and apply the top 5 or all top scores logic
    top_ranked_with_ties_df = (
        valid_df.groupby(
            ['Reference article name', 'Reference text in main article', 'Sentiment'], as_index=False
        ).apply(top_5_or_all_top_scores, threshold=threshold).reset_index(drop=True)
    )

    if change_to_add:
        # Send top-ranked output to an Excel file
        xlsx = top_5 + '.xlsx'
        records1 = top_ranked_with_ties_df.to_dict(orient='records')
        upsert_database_and_collection(uri, db.name, top_5, records1)
        valid_xlsx = valid_collection_name + '.xlsx'
        records2 = valid_df.to_dict(orient='records')
        upsert_database_and_collection(uri, db.name, valid_collection_name, records2)
    else:
        # Send top-ranked output to an Excel file
        xlsx = top_5 + '.xlsx'
        records1 = top_ranked_with_ties_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, top_5, records1)
        valid_xlsx = valid_collection_name + '.xlsx'
        records2 = valid_df.to_dict(orient='records')
        replace_database_collection(uri, db.name, valid_collection_name, records2)

    # Combine invalid rows and matches into one DataFrame
    invalid_df = pd.concat([pd.DataFrame(invalid_rows), matches_df], ignore_index=True)
    invalid_xlsx = not_match + '.xlsx'
    records3 = invalid_df.to_dict(orient='records')
    insert_documents(uri, db.name, not_match, records3)

    
