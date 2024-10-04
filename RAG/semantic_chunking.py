from semantic_router.encoders import AzureOpenAIEncoder
from dotenv import load_dotenv
import os
import subprocess
import time
import logging
from semantic_chunkers import StatisticalChunker
import asyncio
import aiohttp
from tqdm.asyncio import tqdm_asyncio
import numpy as np
import pandas as pd
from tqdm import tqdm


# Load environment variables from .env file
load_dotenv()

# Configure logging to display information
logging.basicConfig(level=logging.INFO)

# Azure configurations from environment variables
az_path = os.getenv("az_path")  # Path to Azure CLI
endpoint = os.getenv("endpoint")  # Azure OpenAI endpoint
api_version = os.getenv("ver")  # Azure API version
embed_model = os.getenv("embed_model")  # Model name for embeddings

# Global variables to track token and its expiry
access_token = None
token_expiry_time = None
token_lock = asyncio.Lock()
encoder = None

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

# Async function to refresh token if needed
async def refresh_token_if_needed():
    global access_token, token_expiry_time, encoder

    async with token_lock:
        # Check if the token has expired or is not set
        if access_token is None or time.time() > token_expiry_time:
            logging.info("Access token has expired or not set. Refreshing token...")

            # Fetch a new access token
            new_token = get_azure_access_token()
            if new_token:
                access_token = new_token
                token_lifetime = 1800  # Token lifetime in seconds (Adjust to actual lifetime)
                token_expiry_time = time.time() + token_lifetime

                # Update the environment variable with the new token
                os.environ['AZURE_OPENAI_API_KEY'] = access_token
                logging.info(f"Access token refreshed successfully. New token expires at {time.ctime(token_expiry_time)}.")

                # Update the encoder's API key if already initialized
                if encoder is not None:
                    encoder.api_key = access_token
                    logging.info("Azure OpenAI encoder updated with new access token.")
                else:
                    encoder = AzureOpenAIEncoder(
                        deployment_name=embed_model,
                        model='text-embedding-3-large',
                        api_key=access_token,
                        azure_endpoint=endpoint,
                        api_version=api_version
                    )
                    logging.info("Azure OpenAI encoder initialized successfully.")
            else:
                logging.error("Failed to refresh access token.")
                return False
    return True

# Function to retry operations with token refresh on Unauthorized error
async def retry_on_exception(func, *args, max_retries=3, retry_delay=2, **kwargs):
    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(f"Attempting {func.__name__} (Attempt {attempt + 1}/{max_retries})...")
            await refresh_token_if_needed()  # Ensure the token is refreshed before each attempt
            return await func(*args, **kwargs)
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                logging.warning("Unauthorized error detected. Refreshing access token and retrying...")
                await refresh_token_if_needed()
            attempt += 1
            logging.error(f"Attempt {attempt} failed with error: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
    logging.error(f"All {max_retries} attempts failed for {func.__name__}.")
    return None

async def initialize_encoder():
    global encoder
    if encoder is None:
        success = await refresh_token_if_needed()  # Ensure token is valid
        if success:
            encoder = AzureOpenAIEncoder(
                deployment_name=embed_model,
                model='text-embedding-3-large',
                api_key=access_token,
                azure_endpoint=endpoint,
                api_version=api_version
            )
            logging.info("Azure OpenAI Encoder initialized successfully.")
        else:
            logging.error("Failed to initialize encoder due to token refresh issues.")


# Function to perform semantic chunking using the initialized encoder
async def semantic_chunk(content):
    global encoder
    if encoder is None:
        await initialize_encoder()
    chunker = StatisticalChunker(encoder=encoder)
    chunks_async = await chunker.acall(docs=[content])

    # Process and return the chunked content
    chunked = []
    for chunk in chunks_async[0]:
        c = chunk.splits
        k = ''.join(c)
        chunked.append(k)
    await asyncio.sleep(1)  # Add a 1-second delay
    logging.info("Chunking completed for one document. Added a 1-second delay before next operation.")
    return chunked

MAX_RETRIES = 3

# Wrapper async function for semantic chunking with error handling
async def semanchunk(text, doc_index, failed_docs, retries=0):
    try:
        return await semantic_chunk(text)  # Call the async semantic_chunk function
    except Exception as e:
        logging.error(f"Error in semanchunk for document index {doc_index}: {e}")
        
        # Add the failed document to the failed_docs list for retrying later
        if retries < MAX_RETRIES:
            failed_docs.append((doc_index, text, retries + 1))  # Increment retry count
        else:
            logging.warning(f"Document index {doc_index} failed after {retries} retries.")
        return None

# Async function to process each batch of the DataFrame
async def process_batch(batch_df, semaphore, failed_docs):
    async with semaphore:
        # Use tqdm_asyncio to track progress within a batch
        tasks = [semanchunk(row['Text Content'], idx, failed_docs) for idx, row in batch_df.iterrows()]
        return await tqdm_asyncio.gather(*tasks, desc="Processing Rows in Batch", leave=False)

# Async function to process the DataFrame in batches
async def process_dataframe_in_batches_async(df, batch_size=10, batch_delay=2):
    # Split the DataFrame into batches
    num_batches = int(np.ceil(len(df) / batch_size))
    batch_dfs = [df[i*batch_size:(i+1)*batch_size] for i in range(num_batches)]

    all_results = [None] * len(df)  # Placeholder for storing results in the correct order
    failed_docs = []  # List to keep track of failed documents for retry
    semaphore = asyncio.Semaphore(5)  # Limit the number of concurrent batches processed

    # Use standard tqdm for processing batches
    for i, batch in enumerate(tqdm(batch_dfs, desc="Processing Batches", unit="batch", total=num_batches)):
        batch_results = await process_batch(batch, semaphore, failed_docs)
        # Store results in the original DataFrame's order
        for idx, result in zip(batch.index, batch_results):
            all_results[idx] = result
        await asyncio.sleep(batch_delay)  # Add a delay between batches to avoid hitting rate limits

    # Retry failed documents after processing all batches
    await retry_failed_documents(failed_docs, all_results)

    return all_results

# Async function to retry failed documents after initial processing
async def retry_failed_documents(failed_docs, all_results):
    retry_count = 0

    # Continue retrying until all documents are processed or max retries are reached
    while failed_docs and retry_count < MAX_RETRIES:
        logging.info(f"Retrying {len(failed_docs)} failed documents (Attempt {retry_count + 1}/{MAX_RETRIES})...")
        current_failed_docs = failed_docs.copy()  # Create a copy to avoid modification issues
        failed_docs.clear()  # Clear the list for this retry attempt

        # Use tqdm to track retry progress
        for doc_index, text, retries in tqdm(current_failed_docs, desc=f"Retrying Failed Documents (Attempt {retry_count + 1})"):
            # Retry processing the failed document
            try:
                result = await semanchunk(text, doc_index, failed_docs, retries=retries)
                if result is not None:
                    all_results[doc_index] = result  # Update result in the main results list
            except Exception as e:
                logging.error(f"Failed to retry document index {doc_index} again: {e}")
        
        retry_count += 1

# Synchronous wrapper function to process the DataFrame
def process_dataframe_sc(df, batch_size=10, batch_delay=2):
    # Run the async function synchronously
    results = asyncio.run(process_dataframe_in_batches_async(df, batch_size=batch_size, batch_delay=batch_delay))
    # Assign results back to the DataFrame
    df['text_chunks'] = results
    return df