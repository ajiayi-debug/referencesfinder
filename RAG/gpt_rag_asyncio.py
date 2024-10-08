import os
import asyncio
import subprocess
import logging
import time
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

# Load environment variables
load_dotenv()

# Configure logging to display information
logging.basicConfig(level=logging.INFO)

# Load environment variables for Azure configuration
az_path = os.getenv("az_path")  # Azure CLI path
endpoint = os.getenv("endpoint")  # Azure endpoint
api_version = os.getenv("ver")  # Azure API version

# Log environment variables for debugging
logging.info(f"az_path: {az_path}")
logging.info(f"endpoint: {endpoint}")
logging.info(f"api_version: {api_version}")

# Global variables to keep track of access token and its expiry
access_token = None
token_expiry_time = None
token_lock = asyncio.Lock()
async_client= None

iteration_count = 0  # Keeps track of the number of iterations
max_iterations_before_reset = 50  # Adjust this number based on your observations and use case

async def check_and_reset_client():
    global iteration_count

    if iteration_count >= max_iterations_before_reset:
        logging.info("Resetting client due to high number of iterations to prevent resource leaks.")
        await initialize_client()  # Re-initialize the client
        iteration_count = 0 

# Function to get Azure access token using Azure CLI
def get_azure_access_token():
    try:
        logging.info("Fetching Azure OpenAI access token using Azure CLI...")
        result = subprocess.run(
            ['az', 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            logging.error(f"Failed to fetch access token. Error: {result.stderr.decode('utf-8')}")
            return None
        token = result.stdout.decode('utf-8').strip()
        if not token:
            logging.error("No access token received. Ensure your Azure CLI is configured correctly.")
            return None
        logging.info("Access token retrieved successfully.")
        return token
    except Exception as e:
        logging.error(f"Exception occurred while fetching access token: {e}")
        return None

# Function to refresh the token if it has expired or is not set
async def refresh_token_if_needed():
    global access_token, token_expiry_time, async_client

    # Acquire the token lock to ensure only one process is refreshing the token at a time
    async with token_lock:
        # Check if the token has expired or is not set
        if access_token is None or time.time() > token_expiry_time - 300:  # Refresh 5 mins before expiry
            logging.info("Access token has expired or is about to expire. Refreshing token...")

            # Fetch a new access token
            new_token = get_azure_access_token()
            if new_token:
                access_token = new_token

                # Set token lifetime (e.g., 25 minutes for a 30-minute token) to leave buffer time
                token_lifetime = 1500  # Token lifetime in seconds (e.g., 25 minutes)
                token_expiry_time = time.time() + token_lifetime

                # Update the environment variable with the new token
                os.environ['AZURE_OPENAI_API_KEY'] = access_token
                logging.info(f"Access token refreshed successfully. New token expires at {time.ctime(token_expiry_time)}.")

                # Re-initialize the async client with the new token
                async_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=access_token,  # Use the refreshed token here
                    api_version=api_version
                )
                logging.info("Async Azure OpenAI client re-initialized successfully after token refresh.")
            else:
                logging.error("Failed to refresh access token.")
                return False
    return True


# Async client initialization
async_client = None
async def initialize_client():
    global async_client
    try:
        await refresh_token_if_needed()  # Ensure token is valid before initializing
        async_client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=access_token,  # Use the refreshed token here
            api_version=api_version
        )
        logging.info("Async Azure OpenAI client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Azure OpenAI client: {e}")
        exit(1)

def extract_retry_after(exception):
    """
    Extracts the Retry-After delay from an exception or response headers.

    Args:
        exception (Exception): The exception that contains the error details.

    Returns:
        int: The retry delay in seconds if found, otherwise None.
    """
    # Check if the exception has a response attribute (usually HTTP exceptions)
    if hasattr(exception, 'response') and exception.response is not None:
        # Try to get the Retry-After header from the response
        retry_after = exception.response.headers.get('Retry-After')
        if retry_after:
            try:
                # Retry-After header can be a number of seconds or a date string
                # Convert to integer seconds if possible
                return int(retry_after)
            except ValueError:
                # If it's not an integer, it might be a date string. Parse it if needed.
                logging.warning(f"Retry-After header is not an integer: {retry_after}. Using default delay.")
    
    # If no retry-after header is found, return None
    return None


# Asynchronous retry function for async functions
async def async_retry_on_exception(func, *args, max_retries=3, retry_delay=30, **kwargs):
    global iteration_count
    attempt = 0
    current_delay = retry_delay

    while attempt < max_retries:
        try:
            logging.info(f"Attempting {func.__name__} (Attempt {attempt + 1}/{max_retries}) with delay {current_delay}s...")
            await refresh_token_if_needed()  # Refresh token if needed before each attempt
            
            # Reset client if too many iterations have been reached
            await check_and_reset_client()
            
            # Try executing the async function
            result = await func(*args, **kwargs)
            
            # Increment iteration count on successful execution
            iteration_count += 1
            return result

        except Exception as e:
            error_message = str(e)
            logging.error(f"Error encountered: {error_message}")

            # Handle 401 errors specifically
            if "401" in error_message or "Unauthorized" in error_message:
                logging.warning("Unauthorized error detected. Refreshing access token and retrying...")
                await refresh_token_if_needed()
                await initialize_client()
                current_delay = retry_delay  # Reset delay after re-authentication
            # Handle rate limits (429 errors)
            elif "429" in error_message or "Too Many Requests" in error_message:
                logging.warning("Rate limit error detected. Applying exponential backoff...")
                retry_after = extract_retry_after(e)
                if retry_after:
                    logging.info(f"Retrying after {retry_after} seconds as specified by the server.")
                    current_delay = retry_after
                else:
                    logging.warning(f"No Retry-After header found. Using exponential backoff delay of {current_delay}s.")

            # Increment attempt counter and increase delay
            attempt += 1
            logging.error(f"Attempt {attempt} failed with error: {e}. Retrying in {current_delay} seconds...")
            await asyncio.sleep(current_delay)
            current_delay *= 2  # Exponential backoff if no Retry-After header was found

    logging.error(f"All {max_retries} attempts failed for {func.__name__}. Returning None.")
    return None



# Asynchronous function to get responses from the Azure OpenAI API
async def retriever_and_siever_async(chunk, ref):
    try:
        pro = """
        Compare the 'Reference Article Text' (which is a chunk of the reference article) to the 'Text Referencing The Reference Article' (which cites the reference article). Identify which parts of the 'Reference Article Text' are being cited or referenced by the 'Text Referencing The Reference Article.'

        By 'citing,' we mean that the 'Text Referencing The Reference Article' refers to or aligns with the information, facts, or concepts in the 'Reference Article Text.' The match can be direct, paraphrased, or conceptually similar.

        Guidelines:
        - Extract ALL relevant parts of the 'Reference Article Text' (chunk) that is being referenced in the 'Text Referencing The Reference Article.' You may output the whole 'Reference Article Text' (chunk) if the whole chunk is relevant.
        - The match does not need to be exact; it can be a paraphrased or conceptually aligned statement.
        - Consider not only direct references, but also cases where the 'Text Referencing The Reference Article' discusses related facts or concepts in different wording.
        - If no part of the 'Reference Article Text' is cited, respond with 'no'.

        Important Note:
        There might be cases where the phrasing between the 'Reference Article Text' and the 'Text Referencing The Reference Article' differs, but the underlying concepts are aligned. For example, if the 'Reference Article Text' discusses gas production due to bacterial fermentation of lactose and the 'Text Referencing The Reference Article' discusses bloating and flatulence after lactose ingestion, these are conceptually aligned, and the relevant portion from the 'Reference Article Text' should be extracted.

        Example of Matching Case:

        Input:
        'Reference Article Text: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Lactose intolerance. Lactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI). However, the two must not be confused and the causes of symptoms must be considered separately. Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).

        Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

        Output:
        'Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).'

        Example of Non-Matching Case (When to Respond with 'No'):

        Input:
        'Reference Article Text: Lactase persistence is common among populations of Northern European descent. The LCT −13’910:C/C genotype is associated with the ability to digest lactose in adulthood.

        Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

        Output:
        'no'

        Why this case results in 'no':
        In this case, the 'Reference Article Text' discusses lactase persistence and a genetic factor related to lactose digestion, while the 'Text Referencing The Reference Article' discusses gas formation due to bacterial fermentation of lactose. These are different concepts, and no alignment exists between the two texts. Therefore, the correct response is 'no.'
        
        Output ONLY the extraction. (the quoted texts after Output: in examples shown).
        """

        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": pro},
                {"role": "user", "content": f"Reference Article Text: {chunk}, Text Referencing The Reference Article: {ref}"}
            ],
            "temperature": 0
        }

        # Make an asynchronous API call using the async client
        response = await async_client.chat.completions.create(**data)
        return response.choices[0].message.content.lower()

    except Exception as e:
        logging.error(f"Exception during API call: {e}")
        return 'api error'

async def call_retrieve_sieve_with_async(chunk, ref):
    await initialize_client()  # Initialize the async client first
    
    result = await async_retry_on_exception(retriever_and_siever_async, chunk, ref)
    return result



async def keyword_search_async(text):
    try:
        #original
        kws1="What are the keywords in the Text? Take note these keywords will be used for a graph search in semantic scholar. Output the keywords ONLY."
        #Making keywords a focus on main topic - idea is to narrow down focus - more accurate papers returned
        kws2= f"""
        What are the main topics in the Text? Take note that these topics will be used as keywords for keyword searching. Output the topics as keywords and ONLY output the keywords with them being separated by commas if there are more than one keyword.
        """
        kws3="""What are the main topics in the text? The topics should be used as keywords for keyword searching. Output the topics as keywords and only output the keywords as a list. If certain topics are closely related, group them together as a single string inside the main list.

        Rules:

        1. Group closely related topics (e.g., "prebiotics" and "probiotics") into a single string like 'prebiotics, probiotics'.
        2. If a topic stands on its own (e.g., "lactose tolerance"), list it separately.
        3. Always format the output as a single list of strings.
        Example: Text: "A proportion of the world’s population is able to tolerate lactose as they have a genetic variation that ensures they continue to produce sufficient quantities of the enzyme lactase after childhood."
        Output: ['lactose tolerance', 'genetic variation, enzyme lactase', 'lactose tolerance, childhood']
        """
        kws4="""
        What are the keywords in terms of topics for the Text? Use the keywords to write keyword searches based on the keywords identified from the Text. Combine keywords if you think they relate to each other. 
        Output the keyword searches as a list of strings ONLY in the format: ['lactase activity restoration', 'lactase activity recovery', ...]
        """
        data={
            "model":"gpt-4o",
            "messages":[
                {"role": "system", "content": kws3},
                {"role": "user", "content": [{"type": "text", "text": f"Text:{text}" }]}
                #{"role": "user", "content": [{"type": "text", "text": kws2}]}
            ],
            "temperature":0
        }
        response = await async_client.chat.completions.create(**data)
        return response.choices[0].message.content.lower()

    except Exception as e:
        logging.error(f"Exception during API call: {e}")
        return 'api error'

async def call_keyword_search_async(text):
    await initialize_client()  # Initialize the async client first
    
    result = await async_retry_on_exception(keyword_search_async, text)
    return result