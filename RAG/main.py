from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from RAG.call_mongodb import *
from RAG.expert_decision import *
import certifi
import datetime as datetime

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
collection_compare = db['merged']
collection_replace=db['replace']

# Helper function to convert MongoDB documents to JSON-serializable format
def serialize_document(document):
    for key, value in document.items():
        if isinstance(value, ObjectId):
            document[key] = str(value)
    return document

def serialize_ids(document):
    """
    Recursively searches for 'id' or '_id' keys in a nested document
    and serializes them if they are ObjectIds.
    """
    if isinstance(document, dict):
        return {
            key: serialize_ids(value) if key not in {"_id", "id"} else str(value) if isinstance(value, ObjectId) else value
            for key, value in document.items()
        }
    elif isinstance(document, list):
        return [serialize_ids(item) for item in document]
    else:
        return document

# Fetch data for expert decision from MongoDB
@app.get("/data")
async def get_data():
    try:
        documents = await collection_take.find().to_list(200)
        data = [serialize_document(doc) for doc in documents]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

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

class Reference(BaseModel):
    id: str
    articleName: str
    authors: str
    date: int

class ReplacementTask(BaseModel):
    statement: str
    oldReferences: List[Reference]
    newReferences: List[Reference]

#send selected data to mongo db then merge w new data for comparison
@app.post("/save_selected_articles")
async def save_selected_articles(selected_articles: List[Article]):
    articles_to_insert = [article.dict() for article in selected_articles]

    # Remove `await` if `replace_database_collection` is synchronous
    replace_database_collection(uri, db.name, 'selected_papers', articles_to_insert)
    merge_old_new('selected_papers','Original_reference_expert_data','collated_statements_and_citations','merged')

    return {"message": "Selected articles saved successfully."}

#Fetch selected new data w matching old data for comparison from MongoDB
@app.get("/joindata")
async def get_select_data():
    try:
        documents = await collection_compare.find().to_list(200)
        data = [serialize_ids(doc) for doc in documents]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

#send replacement pair/one to many to database to update article
@app.post("/addReplacementTask")
async def send_replace(task: ReplacementTask):
    """
    Handles the addition of a single replacement task.
    Args:
        task (ReplacementTask): The JSON payload for the replacement task.
    Returns:
        dict: Success message or error details.
    """
    try:
        # Convert the single task to a dictionary
        task_dict = task.dict()

        # Extract data for logging or further processing
        statement = task.statement
        old_references = task.oldReferences
        new_references = task.newReferences

        # Log the received data for debugging
        print(f"Statement: {statement}")
        print(f"Old References: {old_references}")
        print(f"New References: {new_references}")

        # Insert into MongoDB
        collection_replace.insert_one(task_dict)

        # Log replacement logic for debugging
        for old_ref in old_references:
            for new_ref in new_references:
                print(f"Replacing {old_ref.articleName} with {new_ref.articleName}")

        # Return success response
        return {"message": "Replacement task successfully processed", "status": "success"}

    except Exception as e:
        # Handle any errors during processing
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#Send selected data to edit the .txt 
@app.post("/finalize")
def finalize_data():
    try:
        # Call the formatting function
        formatting()
        return {"message": "Formatting and reference update completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
#arranging directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Project root directory

@app.get("/file/{subpath:path}")
async def get_file(subpath: str):
    """
    Serve files from the project root and its subdirectories.
    """
    file_path = PROJECT_ROOT / subpath
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# Disconnect from MongoDB when the application stops
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
