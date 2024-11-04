from process_and_embed import *
from gpt_retrievesieve import *
from semantic_scholar_keyword_search import *
from process_ref import *
import time
import logging
import asyncio

"""Sanity checking"""
"""Get the statements and their respective reference articles and send to mongodb"""
# logging.info('Finding initial references')
get_statements()
# asyncio.run(asyncio.sleep(60))
"""Allow user to add to mongodb for missing statements and their respective references"""

"""process documents, noembed means we are not using embedding in retrieval and generate process but just to semantically chunk"""
# logging.info('Chunking Initial reference articles')
# process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')
# asyncio.run(asyncio.sleep(60))

# """retrieve and sieve using gpt 4o"""
# logging.info("Comparing chunks with statements referencing the chunks' reference article in the main article")
# retrieve_sieve_references(collection_processed_name='chunked_noembed',valid_collection_name='Agentic_sieved_RAG_original', invalid_collection_name='No_match_agentic_original')
# asyncio.run(asyncio.sleep(60))

# """Finding new references and checking them"""
# """make keywords from statements then do keyword search and download"""
# logging.info('Searching for new references using statements')
# search_and_retrieve_keyword('Agentic_sieved_RAG_original', 'new_ref_found_Agentic_3')
# asyncio.run(asyncio.sleep(60))

"""Process new documents, noembed means we are not using embedding in retrieval and generate process but just to semantically chunk"""
logging.info('Chunking new reference articles')
process_pdfs_to_mongodb_noembed_new(files_directory='papers', collection1='new_chunked_noembed_3')
asyncio.run(asyncio.sleep(60))

"""retrieve and sieve using gpt 4o"""
logging.info("Comparing chunks with statements used to retrieve chunks that support/oppose statements")
retrieve_sieve_references_new(collection_processed_name='new_chunked_noembed_3',new_ref_collection='new_ref_found_Agentic_3',valid_collection_name='Agentic_sieved_RAG_new_support_nosupport_confidence', invalid_collection_name='No_match_agentic_new3_confidence',not_match='no_match3_confidence')

"""Clean the data for ranking (remove hallucinations as well) as well as obtain df of statements that need to be retried due to poor retrieved paper quality"""
logging.info("Checking if any statement that has found paper needs to re-try keyword search as well as clean up hallucinations AND rank the sived portions")
cleaning('Agentic_sieved_RAG_new_support_nosupport_confidence','no_match3_confidence','top_5')


"""
Approach 3:
Papers downloaded = 163
Papers that support = 57

Approach 2:
Papers downloaded = 155
Papers that support =44 
"""
