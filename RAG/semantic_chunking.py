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
import httpx
import random
import openai
from openai import AuthenticationError
from .token_manager import get_or_refresh_token 

# Load environment variables from .env file
load_dotenv()

# Configure logging to display information
logging.basicConfig(level=logging.INFO)

# Azure configurations from environment variables
az_path = os.getenv("az_path")  # Path to Azure CLI
endpoint = os.getenv("endpoint")  # Azure OpenAI endpoint
api_version = os.getenv("ver")  # Azure API version
embed_model = os.getenv("embed_model")  # Model name for embeddings

# Global variables
encoder = None
iteration_count = 0  # Keeps track of the number of iterations
max_iterations_before_reset = 50  # Adjust this number based on your observations and use case

# Loading bar so you won't wait blindly
async def async_delay_with_loading_bar(delay_seconds):
    """
    Asynchronously delay for a given number of seconds while displaying a loading bar.

    Args:
        delay_seconds (int): Number of seconds to wait with the loading bar.
    """
    for _ in tqdm_asyncio(range(delay_seconds), desc=f"Waiting for {delay_seconds} seconds", unit="s"):
        await asyncio.sleep(1)

async def initialize_encoder():
    global encoder
    encoder = None
    await get_or_refresh_token()  # Ensure token is valid
    access_token = os.environ.get('AZURE_OPENAI_API_KEY')
    if access_token:
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

# Function to retry operations with token refresh on Unauthorized error
async def retry_on_exception(func, *args, max_retries=3, retry_delay=10, **kwargs):
    global iteration_count
    attempt = 0
    base_delay = retry_delay
    while attempt < max_retries:
        try:
            logging.info(f"Attempting {func.__name__} (Attempt {attempt + 1}/{max_retries})...")
            await get_or_refresh_token()  # Ensure the access token is valid before each attempt

            # Reset client if too many iterations have been reached
            await check_and_reset_encoder()

            # Try executing the async function
            result = await func(*args, **kwargs)

            # Increment iteration count on successful execution
            iteration_count += 1
            return result

        except AuthenticationError as auth_err:
            logging.error(f"Authentication error occurred: {auth_err}")
            if 'statusCode' in auth_err.error and auth_err.error['statusCode'] == 401:
                logging.warning("Unauthorized error detected. Refreshing access token and retrying...")
                await get_or_refresh_token()
                await initialize_encoder()

        except Exception as e:
            error_message = str(e)
            logging.error(f"Error encountered: {error_message}")

            if "401" in error_message or "Unauthorized" in error_message:
                logging.warning("Unauthorized error detected. Forcefully fetching a new access token and retrying...")
                await get_or_refresh_token()
                await initialize_encoder()
            elif "429" in error_message or "Too Many Requests" in error_message:
                logging.warning("Rate limit error detected. Checking for Retry-After header...")
                retry_after = extract_retry_after(e)  # Extract the Retry-After delay if available
                if retry_after:
                    logging.info(f"Retrying after {retry_after} seconds as specified by the server.")
                    await asyncio.sleep(retry_after)
                else:
                    # Apply exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"No Retry-After header found. Retrying in {delay:.2f} seconds.")
                    await asyncio.sleep(delay)
            else:
                attempt += 1
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.error(f"Attempt {attempt} failed. Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)  # Exponential backoff with jitter

    logging.error(f"All {max_retries} attempts failed for {func.__name__}. Returning None.")
    return None

async def check_and_reset_encoder():
    global iteration_count

    if iteration_count >= max_iterations_before_reset:
        logging.info("Resetting encoder due to high number of iterations to prevent resource leaks.")
        await initialize_encoder()  # Re-initialize the client
        iteration_count = 0

def extract_retry_after(exception):
    """
    Extracts the Retry-After delay from an exception or response headers.
    Args:
        exception (Exception): The exception that contains the error details.
    Returns:
        int: The retry delay in seconds if found, otherwise None.
    """
    if hasattr(exception, 'response') and exception.response is not None:
        retry_after = exception.response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)  # Convert to integer seconds
            except ValueError:
                logging.warning(f"Retry-After header is not an integer: {retry_after}. Using default delay.")
                return None
    return None

# Function to perform semantic chunking using the initialized encoder
async def semantic_chunk(content):
    global encoder
    if encoder is None:
        await initialize_encoder()

    try:
        # Run the StatisticalChunker in a separate thread to avoid blocking the event loop
        chunker = await asyncio.to_thread(StatisticalChunker, encoder=encoder)

        # Call the chunker and process the content
        chunks_async = await asyncio.to_thread(chunker, docs=[content])

        # Process and return the chunked content
        chunked = []
        for chunk in chunks_async[0]:
            c = chunk.splits
            k = ''.join(c)
            chunked.append(k)

        logging.info("Chunking completed for one document.")
        return chunked

    except AuthenticationError as auth_err:
        logging.error(f"Authentication error occurred in StatisticalChunker: {auth_err}")
        if 'statusCode' in auth_err.error and auth_err.error['statusCode'] == 401:
            logging.warning("Unauthorized error detected. Forcefully fetching a new access token and retrying...")

            await get_or_refresh_token()
            await initialize_encoder()

            # Retry the chunking operation after re-initialization
            return await semantic_chunk(content)

    except Exception as e:
        # Catch any other errors, log them, and handle retry if needed
        logging.error(f"Error occurred in StatisticalChunker: {e}")
        raise  # Re-raise the exception or handle it based on the scenario

MAX_RETRIES = 3

# Wrapper async function for semantic chunking with error handling
async def semanchunk(text, doc_index, failed_docs, retries=0):
    try:
        return await retry_on_exception(semantic_chunk, text)  # Call the async semantic_chunk function
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
        # Use asyncio.gather to run all document chunking operations in parallel
        tasks = [semanchunk(row['Text Content'], idx, failed_docs) for idx, row in batch_df.iterrows()]
        results = await asyncio.gather(*tasks, return_exceptions=True)  # Run all tasks concurrently
        return results

# Async function to process the DataFrame in batches
async def process_dataframe_in_batches_async(df, batch_size=5, batch_delay=5):
    """
    Process the DataFrame in batches asynchronously.
    """
    num_batches = int(np.ceil(len(df) / batch_size))
    batch_dfs = [df[i * batch_size:(i + 1) * batch_size] for i in range(num_batches)]

    all_results = [None] * len(df)  # Placeholder for storing results in the correct order
    failed_docs = []  # List to keep track of failed documents for retry
    semaphore = asyncio.Semaphore(3)  # Limit the number of concurrent batches processed

    # Use standard tqdm for processing batches
    for i, batch in enumerate(tqdm(batch_dfs, desc="Processing Batches", unit="batch", total=num_batches)):
        batch_results = await process_batch(batch, semaphore, failed_docs)
        # Store results in the original DataFrame's order
        for idx, result in zip(batch.index, batch_results):
            all_results[idx] = result
        await initialize_encoder()
        logging.info(f"Chunking completed for one batch. Added a {batch_delay}-second delay before next operation.")
        await async_delay_with_loading_bar(batch_delay)

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
def process_dataframe_sc1(df, batch_size=5, batch_delay=5):
    # Run the async function synchronously
    results = asyncio.run(process_dataframe_in_batches_async(df, batch_size=batch_size, batch_delay=batch_delay))
    # Assign results back to the DataFrame
    df['text_chunks'] = results
    return df
