from process_and_embed import *
from gpt_retrievesieve import *
from semantic_scholar_keyword_search import *
import time
import logging
import asyncio

"""Sanity checkinng"""
"""process documents as usual (no embedding)"""
#logging.info('Chunking Initial reference articles')
#process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')
#time.sleep(5)

"""retrieve and sieve using gpt 4o"""
#logging.info("Comparing chunks with statements referencing the chunks' reference article in the main article")
#retrieve_sieve_references(collection_processed_name='chunked_noembed',valid_collection_name='Agentic_sieved_RAG_original', invalid_collection_name='No_match_agentic_original')
#time.sleep(5)

"""Finding new references and checking them"""
"""make keywords from statements then do keyword search and download"""
#logging.info('Searching for new references using statements')
#search_and_retrieve_keyword('Agentic_sieved_RAG_original', 'new_ref_found_Agentic_3')
#time.sleep(5)
"""Process (no embedding)"""
logging.info('Chunking new reference articles')
asyncio.run(process_pdfs_to_mongodb_noembed_new(files_directory='papers', collection1='new_chunked_noembed_3'))
time.sleep(5) 
"""retrieve and sieve using gpt 4o"""
# logging.info("Comparing chunks with statements used to find the chunks' reference article")
# retrieve_sieve_references_new(collection_processed_name='new_chunked_noembed_3',new_ref_collection='new_ref_found_Agentic_3',valid_collection_name='Agentic_sieved_RAG_new3', invalid_collection_name='No_match_agentic_new3',not_match='no_match3')


"""Approach 3:
Papers downloaded = 203

"""