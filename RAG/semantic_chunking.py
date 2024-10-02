from semantic_router.encoders import AzureOpenAIEncoder
from dotenv import load_dotenv
import os
import subprocess
import time
import logging
from semantic_chunkers import StatisticalChunker

# Load environment variables from .env file
load_dotenv()

# Configure logging to display information
logging.basicConfig(level=logging.INFO)

# Global variables to track token and its expiry
access_token = None
token_expiry_time = None

# Azure configurations from environment variables
az_path = os.getenv("az_path")  # Path to Azure CLI
endpoint = os.getenv("endpoint")  # Azure OpenAI endpoint
api_version = os.getenv("ver")  # Azure API version
embed_model = os.getenv("embed_model")  # Model name for embeddings

# Function to get Azure access token using Azure CLI
def get_azure_access_token():
    try:
        logging.info("Fetching Azure OpenAI access token...")
        # Run the Azure CLI command to get access token
        result = subprocess.run(
            [az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Check if the command was successful
        if result.returncode != 0:
            logging.error(f"Failed to fetch access token. Error: {result.stderr.decode('utf-8')}")
            return None

        # Retrieve the token
        token = result.stdout.decode('utf-8').strip()
        if not token:
            logging.error("No access token received. Ensure your Azure CLI is configured correctly.")
            return None

        logging.info("Access token retrieved successfully.")
        return token
    except Exception as e:
        logging.error(f"Exception occurred while fetching access token: {e}")
        return None

# Function to refresh the token if expired or not set
def refresh_token_if_needed():
    global access_token, token_expiry_time

    # Check if the token has expired or is not set
    if access_token is None or time.time() > token_expiry_time:
        logging.info("Access token has expired or not set. Refreshing token...")
        new_token = get_azure_access_token()
        if new_token:
            access_token = new_token
            token_lifetime = 3600  # Assuming 1 hour token lifetime
            token_expiry_time = time.time() + token_lifetime

            # Update environment variables with the new token
            os.environ['AZURE_OPENAI_API_KEY'] = access_token
            logging.info("Access token refreshed successfully.")
        else:
            logging.error("Failed to refresh access token.")
            exit(1)  # Exit if unable to refresh the token

# Function to retry operations with token refresh on Unauthorized error
def retry_on_exception(func, *args, max_retries=3, retry_delay=2, **kwargs):
    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(f"Attempting {func.__name__} (Attempt {attempt + 1}/{max_retries})...")
            refresh_token_if_needed()  # Ensure the token is refreshed before each attempt
            return func(*args, **kwargs)
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                logging.warning("Unauthorized error detected. Refreshing access token and retrying...")
                refresh_token_if_needed()
            attempt += 1
            logging.error(f"Attempt {attempt} failed with error: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    logging.error(f"All {max_retries} attempts failed for {func.__name__}.")
    return None

# Fetch and set initial access token
refresh_token_if_needed()

# Set up the AzureOpenAIEncoder instance with the refreshed token
encoder = None
def initialize_encoder():
    global encoder
    try:
        refresh_token_if_needed()  # Ensure token is valid before initializing
        encoder = AzureOpenAIEncoder(
            deployment_name=embed_model,
            model='text-embedding-3-large',
            api_key=access_token,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        logging.info("Azure OpenAI Encoder initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Azure OpenAI Encoder: {e}")
        exit(1)

# Initialize the encoder
initialize_encoder()

# Function to perform semantic chunking using the initialized encoder
def semantic_chunk(content):
    def func():
        chunker = StatisticalChunker(encoder=encoder)
        chunks = chunker(docs=[content])

        # Process and return the chunked content
        chunked = []
        for chunk in chunks[0]:
            c = chunk.splits
            k = ''.join(c)
            chunked.append(k)
        return chunked

    return retry_on_exception(func)

