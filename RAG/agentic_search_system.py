from process_and_embed import *
from gpt_retrievesieve import *
from semantic_scholar_keyword_search import *
from process_ref import *
import time
import logging
import asyncio
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']


import logging
import pandas as pd

async def generate_improved_prompt(old_prompt):
    """Call the async rewriter to generate a better prompt."""
    return await call_rewritter_async(old_prompt)

def retrieve_missing_references(valid, retry, reference_df):
    """Retrieve missing references from both `retry` and `reference_df`."""
    # Find references missing from the valid DataFrame
    missing_ref_df = reference_df[
        ~reference_df['Reference text in main article'].isin(valid['Reference text in main article'].values)
    ]

    # Include missing references from `retry` that aren't in `valid`
    missing_refs_retry = retry[
        ~retry['Reference text in main article'].isin(valid['Reference text in main article'].values)
    ]

    if not missing_refs_retry.empty:
        # Merge missing retry references with the reference DataFrame to get Date
        merged_df = pd.merge(
            missing_refs_retry[['Reference text in main article']],
            reference_df,
            on='Reference text in main article',
            how='left'
        )
        # Concatenate with the original missing reference DataFrame
        missing_ref_df = pd.concat([missing_ref_df, merged_df], ignore_index=True)

    return missing_ref_df

def update_database_and_excel(missing_ref_df, uri, db):
    """Update database and save missing references to Excel."""
    send_excel(missing_ref_df, 'RAG', 'missing.xlsx')
    records = missing_ref_df.to_dict(orient='records')
    replace_database_collection(uri, db.name, 'missing', records)

async def process_retry_logic(count, collection_processed_name, new_ref_collection, 
                              valid_collection_name, invalid_collection_name, not_match, reference_df):
    """Manage retries and execute prompt-based keyword searches."""
    old_prompt = """
        What are the keywords in terms of topics for the Text? Use the keywords to write keyword searches 
        based on the keywords identified from the Text. Combine keywords if you think they relate to each other. 
        Output the keyword searches as a list of strings ONLY in the format: 
        ['lactase activity restoration', 'lactase activity recovery', ...]
    """

    # Initial retrieval of references
    retry, valid = retrieve_sieve_references_new_retry(
        collection_processed_name, new_ref_collection, valid_collection_name, 
        invalid_collection_name, not_match
    )

    # Calculate missing references initially
    missing_ref_df = retrieve_missing_references(valid, retry, reference_df)

    # Loop as long as there are retries left or missing references exist
    while count > 0 or not missing_ref_df.empty:
        # Generate new improved prompt
        new_prompt = await generate_improved_prompt(old_prompt)
        # Perform keyword-based search
        df = search_and_retrieve_keyword_agentic(new_prompt)
        # Process new PDFs and update MongoDB collection
        process_pdfs_to_mongodb_noembed_new(files_directory='retry_papers', 
                                            collection1=collection_processed_name)
        # Re-fetch references after processing
        retry, valid = retrieve_sieve_references_new_retry(
            collection_processed_name, new_ref_collection, valid_collection_name, 
            invalid_collection_name, not_match
        )
        # Update the missing references DataFrame
        missing_ref_df = retrieve_missing_references(valid, retry, reference_df)

        count -= 1  # Decrement the count
    return df

def agentic_search(collection_processed_name, new_ref_collection, 
                   valid_collection_name, invalid_collection_name, not_match):
    logging.info("Comparing chunks with statements to find the reference article.")

    # Load collated statements and citations from the database once
    codable_collection = db['collated_statements_and_citations']
    codable_docs = list(codable_collection.find({}, {
        '_id': 1, 'Reference article name': 1, 
        'Reference text in main article': 1, 'Date': 1
    }))

    # Prepare DataFrame of references
    reference_data = [
        (doc.get('Reference text in main article'), 
         doc.get('Reference article name'), 
         doc.get('Date')) 
        for doc in codable_docs
    ]
    reference_df = pd.DataFrame(reference_data, columns=[
        'Reference text in main article', 'Reference article name', 'Date'
    ])

    # Retrieve and sieve references
    retry, valid = retrieve_sieve_references_new_retry(
        collection_processed_name, new_ref_collection, valid_collection_name, 
        invalid_collection_name, not_match
    )

    # Retrieve missing references
    missing_ref_df = retrieve_missing_references(valid, retry, reference_df)

    if not missing_ref_df.empty:
        update_database_and_excel(missing_ref_df, uri, db)

        # Initiate retry logic for keyword extraction and reference retrieval
        meta=asyncio.run(
            process_retry_logic(
                count=3, 
                collection_processed_name='new_chunked_noembed_retryretry', 
                new_ref_collection='new_ref_found_Agentic_retryretry', 
                valid_collection_name='try_again', 
                invalid_collection_name='No_match_agentic_new_confidence_retryretry', 
                not_match='no_match3_confidence_retryretry',
                reference_df=reference_df  # Pass the reference DataFrame to avoid reloading
            )
        )
    else:
        new_keyword = valid.to_dict(orient='records')
        upsert_database_and_collection(uri, db.name, 
                                       'Agentic_sieved_RAG_new_support_nosupport_confidence_retry', 
                                       new_keyword)
        new_meta=meta.to_dict(orient='records')
        upsert_database_and_collection(uri, db.name, 
                                       new_ref_collection, 
                                       new_keyword)