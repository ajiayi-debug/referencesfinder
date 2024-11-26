from fastapi import FastAPI, HTTPException, status
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
from .models import *

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
collection_addition=db['addition']
collection_edit=db['edit']


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



#send selected data to mongo db then merge w new data for comparison
@app.post("/save_selected_articles")
async def save_selected_articles(selected_articles: List[Article]):
    articles_to_insert = [article.dict() for article in selected_articles]

    # Remove `await` if `replace_database_collection` is synchronous
    replace_database_collection(uri, db.name, 'selected_papers', articles_to_insert)
    merge_old_new('selected_papers','Original_reference_expert_data','collated_statements_and_citations','merged')

    return {"message": "Selected articles saved successfully."}

#Fetch selected new data w matching old data for comparison from MongoDB (after selection page)
@app.get("/joindata")
async def get_select_data():
    try:
        documents = await collection_compare.find().to_list(200)
        data = [serialize_ids(doc) for doc in documents]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#add and send addition task to database to update article
@app.post("/addAdditionTask")
async def send_add(task: AdditionTask):
    """
    Handles the addition of a single addition task.
    Args:
        task (AdditionTask): The JSON payload for the addition task.
    Returns:
        dict: Success message or error details.
    """
    try:
        # Convert the single task to a dictionary
        task_dict = task.dict()

        # Extract data for logging or further processing
        statement = task.statement
        new_references = task.newReferences

        # Log the received data for debugging
        print(f"Statement: {statement}")
        print(f"New References: {new_references}")

        # Insert into MongoDB
        collection_addition.insert_one(task_dict)

        # Log replacement logic for debugging
        
        for new_ref in new_references:
            print(f"Adding {new_ref.articleName}")

        # Return success response
        return {"message": "Addition task successfully processed", "status": "success"}

    except Exception as e:
        # Handle any errors during processing
        print(f"Error occurred: {e}")
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
#send edits to update article
@app.post("/addEditTask")
async def send_edit(task: EditTask):
    print("Received Task:", task.dict())
    """
    Handles the addition of a single edit task.
    Args:
        task (AdditionTask): The JSON payload for the addition task.
    Returns:
        dict: Success message or error details.
    """
    try:
        # Convert the single task to a dictionary
        task_dict = task.dict()

        # Extract data for logging or further processing
        statement = task.statement
        edits = task.edits
        newref=task.newReferences
        # Log the received data for debugging
        print(f"Statement: {statement}")
        print(f"Edits: {edits}")
        print(f'new ref:{newref}')

        # Insert into MongoDB
        collection_edit.insert_one(task_dict)


        # Return success response
        return {"message": "Addition task successfully processed", "status": "success"}

    except Exception as e:
        # Handle any errors during processing
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#Send selected data to update article 
@app.post("/finalize")
def finalize_data():
    try:
        # Call the formatting function
        formatting()
        collection_replace.drop()
        collection_addition.drop()
        collection_edit.drop()
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


#edit the output.txt file
@app.put("/api/updateFile", response_model=Dict[str, str])
async def update_output_txt(subpath: str, update: UpdateContent):
    """
    Update the contents of a file in the project directory (e.g., output.txt in output_txt directory).
    """
    try:
        # Construct the file path dynamically
        file_path = PROJECT_ROOT / subpath

        # Ensure the file exists; raise an error if it does not
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {subpath} not found."
            )

        # Ensure the parent directory exists (optional, since we're editing an existing file)
        os.makedirs(file_path.parent, exist_ok=True)

        # Write the new content to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(update.content)

        return {"message": f"File {subpath} updated successfully."}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

# Helper function to serialize MongoDB documents
def serialize_replacement(document):
    return {
        "id": str(document["_id"]),
        "statement": document.get("statement", ""),
        "oldReferences": [
            {
                "id": str(ref.get("id", ObjectId())),
                "articleName": ref.get("articleName", ""),
                "authors": ref.get("authors", ""),
                "date": ref.get("date", 0),
            }
            for ref in document.get("oldReferences", [])
        ],
        "newReferences": [
            {
                "id": str(ref.get("id", ObjectId())),
                "articleName": ref.get("articleName", ""),
                "authors": ref.get("authors", ""),
                "date": ref.get("date", 0),
            }
            for ref in document.get("newReferences", [])
        ],
    }

def serialize_addition(document):
    return {
        "id": str(document["_id"]),
        "statement": document.get("statement", ""),
        "newReferences": [
            {
                "id": str(ref.get("id", ObjectId())),
                "articleName": ref.get("articleName", ""),
                "authors": ref.get("authors", ""),
                "date": ref.get("date", 0),
            }
            for ref in document.get("newReferences", [])
        ],
    }

def serialize_edit(document):
    return {
        "id": str(document["_id"]),
        "statement": document.get("statement", ""),
        "edits": document.get("edits", ""),
        "newReferences": [
            {
                "id": str(ref.get("id", ObjectId())),
                "articleName": ref.get("articleName", ""),
                "authors": ref.get("authors", ""),
                "date": ref.get("date", 0),
            }
            for ref in document.get("newReferences", [])
        ],
    }



# GET /api/replacements
@app.get("/api/replacements", response_model=List[Replacement])
async def get_replacements():
    """
    Retrieve all documents from the Replacements collection.
    """
    try:
        replacements = []
        async for replacement in collection_replace.find():
            serialized = serialize_document(replacement)
            replacements.append(serialized)
        return replacements
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GET /api/additions
@app.get("/api/additions", response_model=List[Addition])
async def get_additions():
    """
    Retrieve all documents from the Additions collection.
    """
    try:
        additions = []
        async for addition in collection_addition.find():
            serialized = serialize_addition(addition)
            additions.append(serialized)
        return additions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GET /api/edits
@app.get("/api/edits", response_model=List[Edit])
async def get_edits():
    """
    Retrieve all documents from the Edits collection.
    """
    try:
        edits = []
        async for edit in collection_edit.find():
            serialized = serialize_edit(edit)
            edits.append(serialized)
        return edits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Disconnect from MongoDB when the application stops
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
