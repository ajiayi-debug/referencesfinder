from process_and_embed import *
from gpt_retrievesieve import *
from semantic_scholar_keyword_search import *
import time
import logging
import asyncio

"""Sanity checkinng"""
"""process documents as usual (no embedding)"""
logging.info('Chunking Initial reference articles')
process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')
time.sleep(60)

"""retrieve and sieve using gpt 4o"""
logging.info("Comparing chunks with statements referencing the chunks' reference article in the main article")
retrieve_sieve_references(collection_processed_name='chunked_noembed',valid_collection_name='Agentic_sieved_RAG_original', invalid_collection_name='No_match_agentic_original')
time.sleep(60)

"""Finding new references and checking them"""
"""make keywords from statements then do keyword search and download"""
logging.info('Searching for new references using statements')
search_and_retrieve_keyword('Agentic_sieved_RAG_original', 'new_ref_found_Agentic_2')
time.sleep(60)
"""Process (no embedding)"""
logging.info('Chunking new reference articles')
process_pdfs_to_mongodb_noembed_new(files_directory='papers', collection1='new_chunked_noembed_2')
time.sleep(60) 
"""retrieve and sieve using gpt 4o"""
logging.info("Comparing chunks with statements used to find the chunks' reference article")
retrieve_sieve_references_new(collection_processed_name='new_chunked_noembed_2',new_ref_collection='new_ref_found_Agentic_2',valid_collection_name='Agentic_sieved_RAG_new2', invalid_collection_name='No_match_agentic_new2',not_match='no_match2')


"""
Approach 3:
Papers downloaded = 163
Papers that support = 57

Approach 2:
Papers downloaded = 155
Papers that support =44 
"""
