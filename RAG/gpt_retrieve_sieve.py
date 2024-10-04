from process_and_embed import *
from gpt_retrievesieve import *
from semantic_scholar_keyword_search import *
import time

"""Sanity checkinng"""
"""process documents as usual (no embedding)"""
#process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')
time.sleep(1)
"""retrieve and sieve using gpt 4o"""
#retrieve_sieve_references(collection_processed_name='chunked_noembed',valid_collection_name='Agentic_sieved_RAG_original', invalid_collection_name='No_match_agentic_original')


"""Finding new references and checking them"""
"""make keywords from statements then do keyword search and download"""
#search_and_retrieve_keyword('Agentic_sieved_RAG_original', 'new_ref_found_Agentic_3')

"""Process (no embedding)"""
process_pdfs_to_mongodb_noembed_new(files_directory='papers', collection1='new_chunked_noembed_3')

"""retrieve and sieve using gpt 4o"""
retrieve_sieve_references_new(collection_processed_name='new_chunked_noembed_3',new_ref_collection='new_ref_found_Agentic_3',valid_collection_name='Agentic_sieved_RAG_new3', invalid_collection_name='No_match_agentic_new3',not_match='no_match3')