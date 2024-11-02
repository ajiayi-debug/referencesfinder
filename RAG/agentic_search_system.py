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


def retrieve_missing_references(valid, retry, statement_df):
    #if there are no papers of any statements where chunks retrieved top score below threshold
    if retry.empty:
        print("All papers found for statements with papers are satisfactory.")
        print('Finding statements that have no papers')
        # Find statements missing from the valid DataFrame
        missing_ref_df = statement_df[
            ~statement_df['Reference text in main article'].isin(valid['Reference text in main article'].values)
        ]
        # Ensure missing_ref_df is unique
        missing_ref_df = missing_ref_df.sort_values('Date', ascending=False).drop_duplicates(subset=['Reference text in main article'], keep='first')
        print(f"Found {len(missing_ref_df)} statement(s) that have no valid papers.")
        return missing_ref_df
    #There are papers where chunks retrieved top score below threshold
    else:
        print("Some papers need to be retried.")
        # Find statements missing from the valid DataFrame
        missing_ref_df = statement_df[
            ~statement_df['Reference text in main article'].isin(valid['Reference text in main article'].values)
        ]

        # Include statements from `retry` that aren't in `valid`
        missing_refs_retry = retry[
            ~retry['Reference text in main article'].isin(valid['Reference text in main article'].values)
        ]

        if not missing_refs_retry.empty:
            # Combine statements from retry and statement_df
            missing_ref_df = pd.concat([missing_ref_df, missing_refs_retry], ignore_index=True)
            # Ensure missing_ref_df is unique
            missing_ref_df = missing_ref_df.sort_values('Date', ascending=False).drop_duplicates(subset=['Reference text in main article'], keep='first')

            print(f"Found {len(missing_ref_df)} statement(s) that need to be retried.")
        else:
            #all statements with papers have valid papers. 
            print("All statements with papers have satisfactory papers.")
            missing_ref_df = missing_ref_df.sort_values('Date', ascending=False).drop_duplicates(subset=['Reference text in main article'], keep='first')

            print(f"Found {len(missing_ref_df)} statement(s) that need to be retried.")

        return missing_ref_df

#update and send data for missing data
def update_database_and_excel(missing_ref_df, uri, db):
    """Update database and save missing references to Excel."""
    send_excel(missing_ref_df, 'RAG', 'missing.xlsx')
    records = missing_ref_df.to_dict(orient='records')
    replace_database_collection(uri, db.name, 'missing', records)

#while loop to perform agentic search a max of three times (stops when all conditions of satisfactory papers found met)
def process_retry_logic(count, collection_processed_name, new_ref_collection, 
                              valid_collection_name, invalid_collection_name, not_match, statement_df, missing_ref_df, threshold):
    #Add original prompt to db
    old_prompt = """
        What are the keywords in terms of topics for the Text? Use the keywords to write keyword searches 
        based on the keywords identified from the Text. Combine keywords if you think they relate to each other. 
        Output the keyword searches as a list of strings ONLY in the format: 
        ['lactase activity restoration', 'lactase activity recovery', ...]
    """
    add_prompt_to_db(uri,db.name,'prompts',old_prompt)

    df = pd.DataFrame()
    # Loop as long as there are retries left or missing references exist
    while count > 0 and not missing_ref_df.empty:
        # Generate new improved prompt using prompt generator and old prompt (to make sure prompt generator improves on old prompt)
        new_prompt = asyncio.run(generate_improved_prompt(old_prompt))
        #Add new prompt to db if it doesnt exist
        add_prompt_to_db(uri,db.name,'prompts',new_prompt)
        #generated prompt is now the new prompt for next loop if necessary
        old_prompt=new_prompt
        # Perform keyword-based search with new prompt generated by prompt generator (that will create new keyword for statement with unsatisfactory papers or no papers found so NEW papers found) and send new meta data to a new collection (because new papers) while adding new meta data to existing collection in mongodb
        search_and_retrieve_keyword_agentic('new_metadata',new_ref_collection,new_prompt)
        # Process new PDFs and add to a new collection
        process_pdfs_to_mongodb_noembed_new(files_directory='retry_paper', 
                                            collection1='agentic_new_chunked',change_to_add=True)
        # Re-fetch new references after processing and add another collection outside original collections for each collection type
        retrieve_sieve_references_new(collection_processed_name='agentic_new_chunked',new_ref_collection='new_metadata',valid_collection_name='new_valid', invalid_collection_name='new_invalid',not_match='new_notmatch')
        # We clean new data in a seperate collection (like their respective new, seperate, collection)
        cleaning(valid_collection_name='new_valid',not_match='new_notmatch',threshold=threshold)
        # Add new found data to existing data to determine if need continue loop since measures whole existing database
        add_to_existing(collection_processed_name_new='agentic_new_chunked',collection_processed_name_original=collection_processed_name,
                    new_ref_collection_new='new_metadata',new_ref_collection_original=new_ref_collection,
                    valid_collection_name_new='new_valid',valid_collection_name_original=valid_collection_name,
                    invalid_collection_name_new='new_invalid',invalid_collection_name_original=invalid_collection_name,
                    not_match_new='new_notmatch',not_match_original=not_match)
        #we calculate missing ref df again
        collection_valid=db[valid_collection_name]
        collection_retry=db['retry']
        documents_valid = list(
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
        valid=pd.DataFrame(documents_valid)
        send_excel(valid,'RAG','final_valid.xlsx')
        documents_retry = list(
            collection_retry.find(
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
        retry=pd.DataFrame(documents_retry)
        # Update the missing references DataFrame from existing valid collection and statement collection (that already has new data added)
        missing_ref_df = retrieve_missing_references(valid, retry, statement_df)

        count -= 1  # Decrement the count

#agentic search function (main function)
def agentic_search(collection_processed_name,new_ref_collection, 
                   valid_collection_name,invalid_collection_name,not_match,threshold=False):
    logging.info("Beginning Agentic Search for statements' keywords that did not return satisfactory papers.")

    # Load collated statements and citations from the database once.
    #these are the statements from the main paper
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
    statement_df = pd.DataFrame(reference_data, columns=[
        'Reference text in main article', 'Reference article name', 'Date'
    ])

    collection_valid=db[valid_collection_name]
    collection_retry=db['retry']
    documents_valid = list(
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
    valid=pd.DataFrame(documents_valid)
    documents_retry = list(
        collection_retry.find(
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
    retry=pd.DataFrame(documents_retry)

    #Find out if any statements have unsatisfactory papers (all papers found unsatisfactory (below threshold for top paper)) or no papers found
    missing_ref_df = retrieve_missing_references(valid, retry, statement_df)
    #If any statements unsatisfactory, start agentic search loop (no paper/unsatisfactory papers)
    if not missing_ref_df.empty:
        update_database_and_excel(missing_ref_df, uri, db)

        # Initiate retry logic for keyword extraction and reference retrieval
        print('Running agentic search loop')
        process_retry_logic(
            count=3, 
            collection_processed_name=collection_processed_name, 
            new_ref_collection=new_ref_collection, 
            valid_collection_name=valid_collection_name, 
            invalid_collection_name=invalid_collection_name, 
            not_match=not_match,
            statement_df=statement_df,
            missing_ref_df=missing_ref_df,
            threshold=threshold 
            )
        print('Finished agentic search loop')
    else:
        #All statements have satisfactory papers. No need for agentic search loop
        print('All statements had satisfactory keywords generated and hence satisfactory search results. Agentic search loop closed')