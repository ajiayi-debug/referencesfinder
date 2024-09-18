from process_and_embed import *
from process_ref import *
from semantic_scholar_keyword_search import *

"""Original article and original references"""
process_pdfs_to_mongodb(files_directory='text', collection1='processed', collection2='processed_and_embed')
process_old_references(collection_processed_name='processed_and_embed', collection_name='find_ref')

""" Search and retrieve new articles from semantic scholar database to folder called papers"""
search_and_retrieve_keyword('find_ref', 'new_ref_found')

"""Using text in main article to find new references"""
process_new_pdfs_to_mongodb(files_directory='papers', collection1='processed_new_ref', collection2='processed_and_embed_new_ref')
process_new_references(collection_processed_name='processed_and_embed_new_ref', new_collection_name='final_new_ref_output', collection_found='new_ref_found')
