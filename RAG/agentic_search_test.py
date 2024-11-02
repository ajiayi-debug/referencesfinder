from agentic_search_system import *
import asyncio

uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']

source_collection_name = "Agentic_sieved_RAG_new_support_nosupport_confidence"
target_collection_name = "test_agentic_search_valid"

duplicate_collection(uri, db.name, source_collection_name, target_collection_name)

delete_documents_by_reference_text(uri,db.name,target_collection_name,'Primary lactose intolerance is the most common form.')

cleaning('test_agentic_search_valid','no_match3_confidence_retry',threshold=76)

#agentic_search(collection_processed_name='new_chunked_noembed_retry',new_ref_collection='new_paper_after_retry',valid_collection_name='test_agentic_search_valid',invalid_collection_name='No_match_agentic_new_confidence_retry',not_match='no_match3_confidence_retry')

