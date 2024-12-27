from pymongo import MongoClient
import certifi
from dotenv import load_dotenv
import os

load_dotenv()

#universal MongoDB client 

class MongoDBClient:
    _client = None

    @staticmethod
    def get_client():
        if MongoDBClient._client is None:
            uri = os.getenv("uri_mongo")
            MongoDBClient._client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
        return MongoDBClient._client
