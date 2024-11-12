from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()  # Load environment variables

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify frontend origin, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Connect to MongoDB
client = AsyncIOMotorClient(os.getenv("uri_mongo"))
db = client["data"]  # Replace with your actual database name
collection = db["expert_data"]  # Replace with the collection name you want to fetch

# Helper function to convert MongoDB documents to JSON-serializable format
def serialize_document(document):
    document["_id"] = str(document["_id"])  # Convert ObjectId to string
    return document

# Fetch data from MongoDB
@app.get("/data")
async def get_data():
    try:
        # Fetch and convert documents
        documents = await collection.find().to_list(200)
        data = [serialize_document(doc) for doc in documents]  # Apply conversion to each document
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Disconnect from MongoDB when the application stops
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
