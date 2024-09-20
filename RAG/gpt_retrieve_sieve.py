from process_and_embed import *
from gpt_retriever import *

#process documents as usual (no embedding)
process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')

#retrieve and sieve using gpt 4o
process_nonembed_references(collection_processed_name='chunked_noembed',collection_name='Agentic_sieved_RAG')
