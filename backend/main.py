from fastapi import FastAPI, HTTPException, status, UploadFile, File, Depends
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from .call_mongodb import *
from .expert_decision import *
import certifi
import datetime as datetime
from .models import *
from .process_ref import get_statements
import shutil
import uuid
from .match import match_texts
from .agentic_initial_check import get_statements_agentic
from .process_and_embed import process_pdfs_to_mongodb_noembed,process_pdfs_to_mongodb_noembed_new
from .gpt_retrievesieve import retrieve_sieve_references, cleaning_initial, retrieve_sieve_references_new, cleaning
from .semantic_scholar_keyword_search import search_and_retrieve_keyword
from .agentic_search_system import agentic_search
from .gpt_rag_asyncio import *
from .semantic_chunking import *
import asyncio
import aiosmtplib
from email.message import EmailMessage
from .internet import internet_event,monitor_internet_connection

load_dotenv()  # Load environment variables

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to verify internet connection
async def verify_internet_connection():
    if not internet_event.is_set():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internet connection lost. Please try again later."
        )

uri = os.getenv("uri_mongo")
client = AsyncIOMotorClient(uri, tls=True, tlsCAFile=certifi.where())  
db = client['data']
collection_take = db["expert_data"] 
collection_compare = db['merged']
collection_replace=db['replace']
collection_addition=db['addition']
collection_edit=db['edit']
collection_replace_display=db['replace_dp']
collection_addition_display=db['addition_dp']
collection_edit_display=db['edit_dp']
collection_extract=db['collated_statements_and_citations']

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")

# Utility function to send emails
async def send_email(to_email: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

@app.on_event("startup")
async def startup_event():
    logging.info("Starting centralized initialization...")
    try:
        # Start monitoring internet connection as a background task
        asyncio.create_task(monitor_internet_connection())
        logging.info("Internet monitoring started.")

        # Refresh token
        await get_or_refresh_token()

        # Initialize GPT
        await initialize_client()

        # Initialize Chunker
        await initialize_encoder()

        logging.info("Initialization complete. All systems ready.")
    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        raise RuntimeError("Application initialization failed.")


#arranging directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Project root directory

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
    
# Directory to save uploaded main articless
UPLOAD_DIRECTORY = "main"

def save_uploaded_pdf(file: UploadFile):
    """
    Saves the uploaded PDF file. Replaces any existing PDF in the uploads directory.
    """
    try:
        # Ensure the upload directory exists
        if not os.path.exists(UPLOAD_DIRECTORY):
            os.makedirs(UPLOAD_DIRECTORY)

        # Remove any existing PDFs in the directory
        for existing_file in os.listdir(UPLOAD_DIRECTORY):
            if existing_file.endswith(".pdf"):
                os.remove(os.path.join(UPLOAD_DIRECTORY, existing_file))

        # Use the original file name but sanitize it
        sanitized_filename = f"{uuid.uuid4()}-{file.filename.replace(' ', '_')}"
        file_path = os.path.join(UPLOAD_DIRECTORY, sanitized_filename)

        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return sanitized_filename, file_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

def serialize_extraction(data):
    return {
        "id": str(data.get("_id")),
        "referenceArticleName": data.get("Reference article name"),
        "referenceTextInMainArticle": data.get("Reference text in main article"),
        "date": data.get("Date"),
        "nameOfAuthors": data.get("Name of authors"),
    }



@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Uploads a PDF file, processes it, and extracts text and data.
    """
    try:
        # Save the uploaded file
        filename, file_path = save_uploaded_pdf(file)
        # Return the filename to the frontend
        return {"filename": filename}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-references/")
async def upload_references(files: List[UploadFile] = File(...)):
    """
    Uploads multiple PDF reference files.
    Allows selection of individual files or files within a folder.
    Saves all PDFs directly into the 'text/' directory without creating subdirectories.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # Define the references directory
    references_dir = Path("text")
    saved_filenames = []

    try:
        # Ensure the references directory exists and clear it
        if references_dir.exists():
            for existing_file in references_dir.iterdir():
                if existing_file.is_file():
                    existing_file.unlink()  # Delete all existing files
                elif existing_file.is_dir():
                    shutil.rmtree(existing_file)  # Delete subdirectories if any

        # Ensure the references directory exists
        references_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            # Validate file type
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail=f"Invalid file type: {file.filename}. Only PDF files are allowed."
                )

            # Extract base filename and sanitize
            base_filename = Path(file.filename).name
            sanitized_filename = f"{uuid.uuid4()}-{base_filename.replace(' ', '_')}"

            # Define the full file path
            file_path = references_dir / sanitized_filename

            # Save the file to the directory
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_filenames.append(sanitized_filename)

        return {"filenames": saved_filenames}

    except HTTPException as he:
        raise he
    except Exception as e:
        # Clean up any partially uploaded files in case of an error
        for filename in saved_filenames:
            try:
                (references_dir / filename).unlink()
            except Exception:
                pass  # If deletion fails, there's not much we can do
        raise HTTPException(status_code=500, detail=f"Error saving files: {str(e)}")

@app.post("/extractdata/", dependencies=[Depends(verify_internet_connection)])
def extract_data():
    try:
        get_statements_agentic()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving data: {str(e)}")

@app.post("/match/")
async def match_file_with_db(request: MatchRequest):
    """
    Matches text from a .txt file retrieved using the existing get_file function
    with MongoDB documents.
    """
    subpath = request.subpath
    file_path = PROJECT_ROOT / subpath
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Load the text from the .txt file
    with open(file_path, "r", encoding="utf-8") as f:
        file_text = f.read()

    # Fetch documents from MongoDB
    db_documents = await collection_extract.find({}).to_list(None) 

    # Perform the matching
    matches = match_texts(file_text, db_documents)

    return {"matches": matches}

@app.get("/pdf/{filename}")
def get_pdf(filename: str):
    """
    Serves the uploaded PDF for viewing.
    """
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404, detail="PDF not found")


@app.put("/extraction/")
def save__extraction_data(updated_data: List[ExtractionData]):
    """
    Replaces the extracted data in the MongoDB collection with the updated data.
    """
    try:
        print("Raw input:", updated_data)
        # Convert data to dictionaries with normalized field names
        data_insert = [item.dict(by_alias=True) for item in updated_data]
        print(data_insert)

        # Replace data in MongoDB
        replace_database_collection(uri, db.name, 'collated_statements_and_citations', data_insert)

        return {"message": "Data saved successfully!", "updated_data": updated_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving data: {str(e)}")


@app.get("/extraction/",response_model=List[dict])
async def fetch_extraction_data():
    """
    Retrieve all documents from the references collection.
    """
    try:
        references = []
        async for reference in collection_extract.find():
            serialized = serialize_extraction(reference)
            references.append(serialized)
        return references
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving references: {str(e)}")


"""Workflow (aka GitHub CI/CD DOOP)"""

#Upload personally found references
@app.post("/upload-external-pdfs/")
async def upload_external_pdfs(files: List[UploadFile] = File(...)):
    """
    Uploads multiple PDF reference files into 'external_pdfs' directory.
    Allows selection of individual files or files within a folder.
    Overwrites the directory by removing all existing content before saving the new files.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # Define the references directory
    references_dir = Path("external_pdfs")
    saved_filenames = []

    try:
        # Ensure the references directory exists and clear it
        if references_dir.exists():
            for existing_file in references_dir.iterdir():
                if existing_file.is_file():
                    existing_file.unlink()  # Delete all existing files
                elif existing_file.is_dir():
                    shutil.rmtree(existing_file)  # Delete subdirectories if any

        # Ensure the references directory exists
        references_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            # Validate file type
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail=f"Invalid file type: {file.filename}. Only PDF files are allowed."
                )

            # Extract base filename and sanitize
            base_filename = Path(file.filename).name
            sanitized_filename = f"{uuid.uuid4()}-{base_filename.replace(' ', '_')}"

            # Define the full file path
            file_path = references_dir / sanitized_filename

            # Save the file to the directory
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_filenames.append(sanitized_filename)

        return {"filenames": saved_filenames}

    except HTTPException as he:
        raise he
    except Exception as e:
        # Clean up any partially uploaded files in case of an error
        for filename in saved_filenames:
            try:
                (references_dir / filename).unlink()
            except Exception:
                pass  # If deletion fails, there's not much we can do
        raise HTTPException(status_code=500, detail=f"Error saving files: {str(e)}")


#exisiting references
@app.post('/embedandchunkexisting', dependencies=[Depends(verify_internet_connection)])
def chunk_existing_references(request: EmailRequest):
    try:
        """process documents, noembed means we are not using embedding in retrieval and generate process but just to semantically chunk"""
        process_pdfs_to_mongodb_noembed(files_directory='text', collection1='chunked_noembed')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error embedding and chunking existing references: {str(e)}")
    return {"status": "Embed & Chunk Existing Referencescompleted successfully."}

@app.post('/evaluateexisting', dependencies=[Depends(verify_internet_connection)])
def evaluate_existing_references(request: EmailRequest):
    try:
        """Retrieve and sieve using GPT-4"""
        retrieve_sieve_references(
            collection_processed_name='chunked_noembed',
            valid_collection_name='Agentic_sieved_RAG_original',
            invalid_collection_name='No_match_agentic_original'
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving and evaluating existing references: {str(e)}"
        )
    
    #Path to the crossref.xlsx file in the project root directory
    file_path = PROJECT_ROOT / 'crossref.xlsx'
    
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="crossref.xlsx not found in the project root directory."
        )
    
    #Return the Excel file directly using FileResponse
    return FileResponse(
        path=str(file_path),
        filename='crossref.xlsx',
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=crossref.xlsx"}
    )
@app.post('/cleanexisting', dependencies=[Depends(verify_internet_connection)])
def clean_existing(request: EmailRequest):
    try:
        """Clean the old references for a summary for comparison when updating articles"""
        cleaning_initial(valid_collection_name='Agentic_sieved_RAG_original', not_match='No_match_agentic_original', top_5='top_5_original')
        """Make pretty for comparison for replacement/addition to citation"""
        make_summary_for_comparison(top_5='top_5_original',expert='Original_reference_expert_data')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning existing references: {str(e)}")
    return {"status": "Cleaning Existing References completed successfully."}
    
#New References
@app.post('/search', dependencies=[Depends(verify_internet_connection)])
def find_new(request: EmailRequest):
    try:
        """Finding new references and checking them"""
        """make keywords from statements then do keyword search and download"""
        search_and_retrieve_keyword('Agentic_sieved_RAG_original', 'new_ref_found_Agentic')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding new references: {str(e)}")
    return {"status":"Search For New References completed successfully."}
    
@app.post('/embedandchunknew', dependencies=[Depends(verify_internet_connection)])
def chunk_new_references(request: EmailRequest):
    try:
        """Process new documents, noembed means we are not using embedding in retrieval and generate process but just to semantically chunk"""
        process_pdfs_to_mongodb_noembed_new(files_directory='papers', collection1='new_chunked_noembed')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error embedding and chunking new references: {str(e)}")
    return {"status":"Embed & Chunk New References completed successfully."}
    
@app.post('/evaluatenew', dependencies=[Depends(verify_internet_connection)])
def evaluate_new_references(request: EmailRequest):
    try:
        """retrieve and sieve using gpt 4o"""
        retrieve_sieve_references_new(collection_processed_name='new_chunked_noembed',new_ref_collection='new_ref_found_Agentic',valid_collection_name='Agentic_sieved_RAG_new_support_nosupport_confidence', invalid_collection_name='No_match_agentic_new_confidence',not_match='no_match_confidence')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving and evaluating new references: {str(e)}")
    return {"status":"Evaluate New References completed successfully."}

@app.post('/cleannew', dependencies=[Depends(verify_internet_connection)])
def clean_new(request: EmailRequest):
    try:
        """Clean the new references for a summary for comparison when updating articles"""
        cleaning('Agentic_sieved_RAG_new_support_nosupport_confidence','no_match_confidence','top_5',threshold=80)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning new references: {str(e)}")
    return {"status":"Cleaning New References completed successfully."}

@app.post('/agenticsearch', dependencies=[Depends(verify_internet_connection)])
def retry_poor_search(request: EmailRequest):
    try:
        """Perform agentic search for poor performance papers or statements that has no papers returned"""
        agentic_search(collection_processed_name='new_chunked_noembed',new_ref_collection='new_ref_found_Agentic',valid_collection_name='Agentic_sieved_RAG_new_support_nosupport_confidence',invalid_collection_name='No_match_agentic_new_confidence',not_match='no_match_confidence',top_5='top_5')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in agentic search for new references: {str(e)}")
    return {"status":"Agentic Search completed successfully."}

@app.post('/expertpresentation', dependencies=[Depends(verify_internet_connection)])
def expert_presentation(request: EmailRequest):
    try:
        """Make a table for data representation"""
        make_pretty_for_expert('top_5','new_ref_found_Agentic','expert_data')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in presentation for new references: {str(e)}")
    return {"status":"Presentation of New References completed successfully."}

# Notification Endpoint
@app.post("/notify")
async def notify_user(request: NotifyRequest):
    if request.success:
        subject = "Workflow Processing Completed Successfully"
        body = (
            "Dear User,\n\n"
            "Your workflow processing has been completed successfully.\n\n"
            "Best regards,\n"
            "Your Team"
        )
    else:
        subject = "Workflow Processing Encountered an Error"
        body = (
            "Dear User,\n\n"
            f"An error occurred during your workflow processing: {request.error}\n\n"
            "Please try again or contact support.\n\n"
            "Best regards,\n"
            "Your Team"
        )

    await send_email(request.email, subject, body)
    return {"status": "email_sent"}


# Fetch data for expert decision from MongoDB
@app.get("/data")
async def get_data():
    try:
        documents = await collection_take.find().to_list(500)
        data = [serialize_document(doc) for doc in documents]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Define the path to the paper directory
BASE_DIR = Path(__file__).resolve().parent  # `backend` directory
PAPER_DIR = BASE_DIR.parent / "papers"       # Sibling `paper` directory

#download paper by paper id
@app.get("/download_paper/{paper_id}")
def download_paper(paper_id: str):
    # Assuming papers are located in a directory one level above FastAPI code
    file_path = PAPER_DIR / f"{paper_id}.pdf"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Paper not found.")
    return FileResponse(path=file_path, filename=f"{paper_id}.pdf", media_type='application/pdf')

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

@app.post("/finalize", dependencies=[Depends(verify_internet_connection)])
def finalize_data():
    try:
        # Call the synchronous formatting function
        print("Step 1: Running the formatting function...")
        formatting()  # If this takes too long, consider converting it to async
        print("Formatting function completed.")

        # Return success response
        return {"message": "Formatting completed successfully."}

    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post('/delete_changes')
async def send():
    try:
        # Drop old collections
        print("Dropping old collections...")
        await collection_replace.drop()
        await collection_addition.drop()
        await collection_edit.drop()
        print("Old collections dropped successfully.")

        # Return success response
        return {"message": "All tasks completed successfully."}

    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



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
            serialized = serialize_replacement(replacement)
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
