from .process_and_embed import *
from .gpt_retrievesieve import *
from .semantic_scholar_keyword_search import *
from .process_ref import *
import time
import logging
import asyncio
from .agentic_search_system import *
from .expert_decision import *
from .agentic_initial_check import get_statements_agentic



# """Sanity checking"""
# """Get the statements and their respective reference articles and send to mongodb"""
# logging.info('Finding initial references')
# get_statements()
# time.sleep(60)
"""Allow user to add to mongodb for missing statements and their respective references"""
#function to add missing statements if necessary (done on frontend)
"""process documents, noembed means we are not using embedding in retrieval and generate process but just to semantically chunk"""
logging.info('Chunking Initial reference articles')
process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')
time.sleep(60)

# """retrieve and sieve using gpt 4o"""
# logging.info("Comparing chunks with statements referencing the chunks' reference article in the main article")
# retrieve_sieve_references(collection_processed_name='chunked_noembed',valid_collection_name='Agentic_sieved_RAG_original', invalid_collection_name='No_match_agentic_original')
# time.sleep(60)

# """Clean the old references for a summary for comparison when updating articles"""
# cleaning_initial(valid_collection_name='Agentic_sieved_RAG_original', not_match='No_match_agentic_original', top_5='top_5_original')

# """Make pretty for comparison for replacement/addition to citation"""
# make_summary_for_comparison(top_5='top_5_original',expert='Original_reference_expert_data')

# """Finding new references and checking them"""
# """make keywords from statements then do keyword search and download"""
# logging.info('Searching for new references using statements')
# search_and_retrieve_keyword('Agentic_sieved_RAG_original', 'new_ref_found_Agentic')
# time.sleep(60)

# """Process new documents, noembed means we are not using embedding in retrieval and generate process but just to semantically chunk"""
# logging.info('Chunking new reference articles')
# process_pdfs_to_mongodb_noembed_new(files_directory='papers', collection1='new_chunked_noembed')
# time.sleep(60)

# """retrieve and sieve using gpt 4o"""
# logging.info("Comparing chunks with statements used to retrieve chunks that support/oppose statements")
# retrieve_sieve_references_new(collection_processed_name='new_chunked_noembed',new_ref_collection='new_ref_found_Agentic',valid_collection_name='Agentic_sieved_RAG_new_support_nosupport_confidence', invalid_collection_name='No_match_agentic_new_confidence',not_match='no_match_confidence')
# time.sleep(60)

# """Clean the data for ranking (remove hallucinations as well) as well as obtain df of statements that need to be retried due to poor retrieved paper quality"""
# logging.info("Checking if any statement that has found paper needs to re-try keyword search as well as clean up hallucinations AND rank the sived portions")
# cleaning('Agentic_sieved_RAG_new_support_nosupport_confidence','no_match_confidence','top_5',threshold=80)
# time.sleep(60)

# """Perform agentic search for poor performance papers or statements that has no papers returned"""
# logging.info('Performing agentic search for poor search results')
# agentic_search(collection_processed_name='new_chunked_noembed',new_ref_collection='new_ref_found_Agentic',valid_collection_name='Agentic_sieved_RAG_new_support_nosupport_confidence',invalid_collection_name='No_match_agentic_new_confidence',not_match='no_match_confidence',top_5='top_5')


# # """Debug statement to see all data in excel form"""

# # send_excel_all(collection_processed_name='new_chunked_noembed',new_ref_collection='new_ref_found_Agentic',valid_collection_name='Agentic_sieved_RAG_new_support_nosupport_confidence',invalid_collection_name='No_match_agentic_new_confidence',not_match='no_match_confidence',top_5='top_5')

# """Make a table for data representation"""
# make_pretty_for_expert('top_5','new_ref_found_Agentic','expert_data')


