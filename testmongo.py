from pymongo import MongoClient
from dotenv import *
import os

load_dotenv()

uri = os.getenv("uri_mongo")

try:
    client = MongoClient(uri)
    db = client.test
    print("Connected to MongoDB Atlas!")
except Exception as e:
    print(f"Error: {e}")
