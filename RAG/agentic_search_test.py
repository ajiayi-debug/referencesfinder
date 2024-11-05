from agentic_search_system import *
import asyncio

uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']


# duplicate_collection_with_drop(uri, db.name, "Agentic_sieved_RAG_new_support_nosupport_confidence", "test_agentic_search_valid")
# duplicate_collection_with_drop(uri, db.name, "new_chunked_noembed", "new_chunked_noembed_retry")
# duplicate_collection_with_drop(uri, db.name, "new_ref_found_Agentic", "new_paper_after_retry")
# duplicate_collection_with_drop(uri, db.name, "No_match_agentic_new_confidence", "No_match_agentic_new_confidence_retry")
# duplicate_collection_with_drop(uri, db.name, "no_match_confidence", "no_match3_confidence_retry")
# duplicate_collection_with_drop(uri, db.name, "top_5", "top_5_test")

#delete_documents_by_reference_text(uri,db.name,target_collection_name,'Primary lactose intolerance is the most common form.')

agentic_search(collection_processed_name='new_chunked_noembed_retry',new_ref_collection='new_paper_after_retry',valid_collection_name='test_agentic_search_valid',invalid_collection_name='No_match_agentic_new_confidence_retry',not_match='no_match3_confidence_retry',top_5='top_5_test',threshold=76)

#test script for agentic search function