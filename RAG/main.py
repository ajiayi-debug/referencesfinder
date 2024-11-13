from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from RAG.call_mongodb import replace_database_collection
import certifi

load_dotenv()  # Load environment variables

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify frontend origin, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uri = os.getenv("uri_mongo")
client = AsyncIOMotorClient(uri, tls=True, tlsCAFile=certifi.where())  # Use AsyncIOMotorClient
db = client['data']
collection_take = db["expert_data"] 
collection_send = db['selected_papers']

# Helper function to convert MongoDB documents to JSON-serializable format
def serialize_document(document):
    document["_id"] = str(document["_id"])  # Convert ObjectId to string
    return document

# Fetch data from MongoDB
@app.get("/data")
async def get_data():
    try:
        documents = await collection_take.find().to_list(200)
        data = [serialize_document(doc) for doc in documents]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# Define the data structure
class Article(BaseModel):
    id: str
    sentiment: str
    sievingByGPT4o: List[str]
    chunk: List[str]
    articleName: str
    statement: str
    summary: str
    authors: str
    date: int
    rating: str



@app.post("/save_selected_articles")
async def save_selected_articles(selected_articles: List[Article]):
    print("Received articles:", selected_articles)
    articles_to_insert = [article.dict() for article in selected_articles]

    # Remove `await` if `replace_database_collection` is synchronous
    replace_database_collection(uri, db.name, 'selected_papers', articles_to_insert)

    return {"message": "Selected articles saved successfully."}


# Disconnect from MongoDB when the application stops
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
