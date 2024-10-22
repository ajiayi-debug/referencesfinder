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


def agentic_search(collection_processed_name='new_chunked_noembed_3',new_ref_collection='new_ref_found_Agentic_3',valid_collection_name='Agentic_sieved_RAG_new_support_nosupport_confidence', invalid_collection_name='No_match_agentic_new3_confidence',not_match='no_match3_confidence'):
    logging.info("Comparing chunks with statements used to find the chunks' reference article")
    retry,valid=retrieve_sieve_references_new_retry(collection_processed_name,new_ref_collection,valid_collection_name, invalid_collection_name,not_match)
    
    count=3
    codable_collection = db['collated_statements_and_citations']

    codable_docs = list(
        codable_collection.find(
            {}, 
            {
                '_id': 1,  # Include _id field
                'Reference text in main article': 1  
            }
        )
    )

    # Extract the 'Reference article name' column into a list
    reference = [doc.get('Reference text in main article') for doc in codable_docs]
    unique_reference = list(set(reference))

    missing_ref= [ref for ref in unique_reference if ref not in valid['Reference text in main article'].values]

    # Create a new DataFrame with the missing names (if any)
    if missing_ref:
        missing_df = pd.DataFrame(missing_ref, columns=['Missing Statements'])
        print("Missing Reference Names added to new DataFrame:")
        print(missing_df)
    else:
        print("No missing names found.")
                        
    missing_refs = retry[~retry['Reference text in main article'].isin(valid['Reference text in main article'])]
    if not missing_refs.empty:
        additional_missing_df = missing_refs[['Reference text in main article']]
        # Rename the column to match `missing_df`
        additional_missing_df.columns = ['Missing Statements']
        # Concatenate with `missing_df`
        missing_df = pd.concat([missing_df, additional_missing_df], ignore_index=True)
        print("Updated Missing Reference Names DataFrame:")
        print(missing_df)
    else:
        print("No additional missing references found in retry DataFrame.")
