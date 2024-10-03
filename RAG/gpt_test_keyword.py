from process_and_embed import *
from gpt_retrievesieve import *
from semantic_scholar_keyword_search import *

"""Finding new references and checking them"""
"""make keywords from statements then do keyword search and download"""
#test_search_and_retrieve_keyword('Agentic_sieved_RAG_original', 'new_ref_found_Agentic',2)

"""Process (no embedding)"""
#process_pdfs_to_mongodb_noembed_new(files_directory='papers', collection1='new_chunked_noembed_2')

"""retrieve and sieve using gpt 4o"""
retrieve_sieve_references_new(collection_processed_name='new_chunked_noembed_2',new_ref_collection='new_ref_found_Agentic',valid_collection_name='Agentic_sieved_RAG_new2', invalid_collection_name='No_match_agentic_new2',not_match='no_match2')