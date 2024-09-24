from process_and_embed import *
from gpt_retriever_siever import *
from gpt_retrievesieve import *

#process documents as usual (no embedding)
#process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')

#retrieve and sieve using gpt 4o
#retrieve_then_sieve_references(collection_processed_name='chunked_noembed',collection_name='Agentic_sieved_RAG')
retrieve_sieve_references(collection_processed_name='chunked_noembed',collection_name='Agentic_sieved_RAG')