import os
import asyncio
import subprocess
import logging
import time
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from openai import AuthenticationError
import httpx

# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Azure configuration
endpoint = os.getenv("endpoint")
api_version = os.getenv("ver")

# Global state and synchronization tools
access_token = None
token_expiry_time = None
async_client = None
token_lock = asyncio.Lock()
refresh_in_progress = asyncio.Event()
global_pause_event = asyncio.Event()
global_pause_event.set()

iteration_count = 0
max_iterations_before_reset = 50
retry_queue = []  # Store failed tasks for retry

# Function to get Azure access token
def get_azure_access_token():
    try:
        logging.info("Fetching Azure OpenAI access token...")
        result = subprocess.run(
            ['az', 'account', 'get-access-token', '--resource', 
             'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            logging.error(f"Failed to fetch access token: {result.stderr.decode('utf-8')}")
            return None
        return result.stdout.decode('utf-8').strip()
    except Exception as e:
        logging.error(f"Error fetching access token: {e}")
        return None

# Refresh token and client
async def refresh_token_and_client():
    global access_token, token_expiry_time, async_client

    async with token_lock:
        if refresh_in_progress.is_set():
            logging.info("Refresh already in progress. Waiting...")
            await refresh_in_progress.wait()
            return

        refresh_in_progress.set()
        global_pause_event.clear()

        try:
            logging.info("Refreshing token and client...")
            new_token = get_azure_access_token()
            if new_token:
                access_token = new_token
                token_expiry_time = time.time() + 1500
                os.environ['AZURE_OPENAI_API_KEY'] = access_token

                async_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=access_token,
                    api_version=api_version
                )
                logging.info("Token refreshed and client re-initialized.")
            else:
                logging.error("Failed to refresh access token.")
        finally:
            refresh_in_progress.clear()
            global_pause_event.set()

# Ensure token is valid
async def ensure_valid_token():
    if access_token is None or time.time() > token_expiry_time - 300:
        logging.info("Token expired or near expiry. Triggering refresh...")
        await refresh_token_and_client()

# Initialize the async client
async def initialize_client():
    await ensure_valid_token()
    logging.info("Async Azure OpenAI client initialized.")

# Reset client after max iterations
async def check_and_reset_client():
    global iteration_count
    if iteration_count >= max_iterations_before_reset:
        logging.info("Resetting client after max iterations.")
        await refresh_token_and_client()
        iteration_count = 0

# Extract Retry-After delay
def extract_retry_after(exception):
    if hasattr(exception, 'response') and exception.response is not None:
        retry_after = exception.response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                logging.warning(f"Retry-After header not an integer: {retry_after}")
    return None

# Asynchronous retry function with storage of failed tasks
async def async_retry_on_exception(func, *args, max_retries=3, retry_delay=10, **kwargs):
    global iteration_count, retry_queue
    attempt = 0

    while attempt < max_retries:
        await global_pause_event.wait()  # Ensure tasks are not paused

        try:
            logging.info(f"Attempt {attempt + 1}/{max_retries} for {func.__name__}...")
            await ensure_valid_token()  # Ensure token is valid

            result = await func(*args, **kwargs)  # Execute the function
            iteration_count += 1
            return result

        except (RuntimeError, AuthenticationError, httpx.HTTPStatusError) as e:
            if isinstance(e, RuntimeError) and "Event loop is closed" in str(e):
                logging.warning("Caught 'Event loop is closed' error. Adding to retry queue.")
                retry_queue.append((func, args, kwargs))
                return None  # Exit early since loop is closed

            if isinstance(e, AuthenticationError) or \
               (isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 401):
                logging.warning("401 Unauthorized error. Refreshing token...")
                await refresh_token_and_client()

            elif isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                retry_after = extract_retry_after(e)
                delay = retry_after if retry_after else retry_delay * 2
                logging.warning(f"Rate limit hit. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        except Exception as e:
            logging.error(f"Unexpected error: {e}")

        attempt += 1
        logging.warning(f"Retrying in {retry_delay} seconds...")
        await asyncio.sleep(retry_delay)

    logging.error(f"All {max_retries} attempts failed for {func.__name__}.")
    retry_queue.append((func, args, kwargs))  # Store failed task for later retry


# Process the retry queue
async def process_retry_queue():
    global retry_queue
    for func, args, kwargs in retry_queue:
        logging.info(f"Retrying stored task: {func.__name__}")
        await async_retry_on_exception(func, *args, **kwargs)
    retry_queue = []

#retriever and siever for oppose and support
async def call_retrieve_sieve_with_async(chunk, ref):
    await initialize_client()
    return await async_retry_on_exception(retriever_and_siever_async, chunk, ref)

#retriever and siever for sanity checking
async def call_retrieve_sieve_with_async_check(chunk, ref):
    await initialize_client()
    return await async_retry_on_exception(retriever_and_siever_async_check, chunk, ref)

# Keyword search function
async def call_keyword_search_async(text):
    await initialize_client()
    result = await async_retry_on_exception(keyword_search_async, text)
    return result
#Get the statements, reference article titles, authors of reference articles and year reference articles released
async def call_get_ref_async(text):
    await initialize_client()
    result = await async_retry_on_exception(get_references_async, text)
    return result

async def call_rerank_support_async(ref,chunk):
    await initialize_client()
    result = await async_retry_on_exception(rerank_support_async, ref,chunk)
    return result


async def call_rerank_oppose_async(ref,chunk):
    await initialize_client()
    result = await async_retry_on_exception(rerank_oppose_async, ref,chunk)
    return result

# Asynchronous function to get responses from the Azure OpenAI API
async def retriever_and_siever_async(chunk, ref):
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
    pro_notpro="""
    Compare the ‘Reference Article Text’ (which is a chunk of the reference article) to the ‘Text Referencing The Reference Article’ (which cites the reference article). Identify which parts of the ‘Reference Article Text’ are being cited, referenced, or opposed by the ‘Text Referencing The Reference Article.’

    By ‘citing’ or ‘referencing,’ we mean that the ‘Text Referencing The Reference Article’ refers to, aligns with, or supports the information, facts, or concepts in the ‘Reference Article Text.’ The match can be direct, paraphrased, or conceptually similar.

    By ‘opposing,’ we mean that the ‘Text Referencing The Reference Article’ provides a viewpoint or information that contradicts or challenges the information in the ‘Reference Article Text.’

    Guidelines:

        •	For cited or referenced parts: Extract ALL relevant parts of the ‘Reference Article Text’ (chunk) that is being referenced in the ‘Text Referencing The Reference Article.’ You may output the whole ‘Reference Article Text’ (chunk) if the whole chunk is relevant. Start the output with 'Support:' if the ‘Text Referencing The Reference Article’ supports or references the ‘Reference Article Text.’
        •	For opposing parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are being opposed by the ‘Text Referencing The Reference Article.’ Focus on portions where the concepts or facts contradict the information provided. Start the output with 'Oppose:' if the ‘Text Referencing The Reference Article’ opposes the ‘Reference Article Text.’
        •	The match or opposition does not need to be exact; it can be a paraphrased or conceptually aligned or opposing statement.
        •	Consider not only direct references but also cases where the ‘Text Referencing The Reference Article’ discusses related facts or concepts in different wording.
        •	If no part of the ‘Reference Article Text’ is cited or opposed, respond with ‘no.’

    Important Note:
    There might be cases where the phrasing between the ‘Reference Article Text’ and the ‘Text Referencing The Reference Article’ differs, but the underlying concepts are aligned (for references) or contradictory (for opposition). For example:

        •	If the ‘Reference Article Text’ discusses gas production due to bacterial fermentation of lactose and the ‘Text Referencing The Reference Article’ discusses bloating and flatulence after lactose ingestion, these are conceptually aligned, and the relevant portion from the ‘Reference Article Text’ should be extracted, starting with 'Support:'
        •	If the ‘Reference Article Text’ supports the idea that lactose intolerance causes significant symptoms, but the ‘Text Referencing The Reference Article’ argues that lactose intolerance is not as widespread or impactful, then the opposing portion should be extracted, starting with 'Oppose:'

    Example of Supporting Case:

    Input:
    ’Reference Article Text: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Lactose intolerance. Lactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI). However, the two must not be confused, and the causes of symptoms must be considered separately. Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).

    Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.’

    Output:
    'Support: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).’

    Example of Opposing Case:

    Input:
    ’Reference Article Text: Lactose intolerance affects around 70 percent of the global population, causing a range of digestive issues that reduce quality of life for those affected.

    Text Referencing The Reference Article: Recent studies show that lactose intolerance affects only a small proportion of the world, and many people who believe they are lactose intolerant can consume dairy without significant symptoms.’

    Output:
    'Oppose: Lactose intolerance affects around 70 percent of the global population, causing a range of digestive issues that reduce quality of life for those affected.’

    Example of Non-Matching Case (When to Respond with ‘No’):

    Input:
    ’Reference Article Text: Lactase persistence is common among populations of Northern European descent. The LCT −13’910:C/C genotype is associated with the ability to digest lactose in adulthood.

    Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.’

    Output:
    ‘no’

    Output ONLY the quoted texts after Output: in examples shown.
    """
    pro_w_confidence="""

    Compare the ‘Reference Article Text’ (which is a chunk of the reference article) to the ‘Text Referencing The Reference Article’ (which cites the reference article). Identify which parts of the ‘Reference Article Text’ are being cited, referenced, or opposed by the ‘Text Referencing The Reference Article.’ Additionally, assign a confidence score (0-100) to each comparison and place it in brackets next to ‘Support’ or ‘Oppose’ if any part of the text 'Support' or 'Oppose' the ‘Text Referencing The Reference Article’.

    By ‘citing’ or ‘referencing,’ we mean that the ‘Text Referencing The Reference Article’ refers to, aligns with, or supports the information, facts, or concepts in the ‘Reference Article Text.’ The match can be direct, paraphrased, or conceptually similar.

    By ‘opposing,’ we mean that the ‘Text Referencing The Reference Article’ provides a viewpoint or information that contradicts or challenges the information in the ‘Reference Article Text.’

    Guidelines:

        1.	For cited or referenced parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are referenced. Start with ‘Support ([Confidence Score]):’.
        2.	For opposing parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are opposed. Start with ‘Oppose ([Confidence Score]):’.
        3.	Provide Justifications: For each confidence score, give a brief reason explaining the score (e.g., strong conceptual alignment, partial overlap, or weak opposition).
        4.	If no match exists, respond with ‘no’.

    Example Outputs with Confidence Scores:

    Supporting Example:
    Input:
    'Reference Article Text: Bacterial fermentation of lactose produces gases like hydrogen, methane, and CO2, impacting GI function.'
    'Text Referencing The Reference Article: Fermentation of lactose in the gut leads to gas production, causing bloating.'
    Output:
    'Support (90): Bacterial fermentation of lactose produces gases like hydrogen, methane, and CO2, impacting GI function.'


    Opposing Example:
    Input:
    'Reference Article Text: “Lactose intolerance affects around 70 percent of the population.'
    'Text Referencing The Reference Article: “Recent studies indicate lactose intolerance affects a small proportion of the population.'
    Output:
    'Oppose (85): Lactose intolerance affects around 70 percent of the population.'


    Non-Matching Case:
    Input:
    'Reference Article Text: “Lactase persistence is common among Northern Europeans.'
    'Text Referencing The Reference Article: “Fermentation of lactose produces gas.'
    Output:
    'no'

    Output ONLY the quoted texts after Output: in examples shown.
    """
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": pro_w_confidence},
            {"role": "user", "content": f"Reference Article Text: {chunk}, Text Referencing The Reference Article: {ref}"}
        ],
        "temperature": 0
    }

    # Make an asynchronous API call using the async client
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content.lower()


async def retriever_and_siever_async_check(chunk, ref):
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
    pro_notpro="""
    Compare the ‘Reference Article Text’ (which is a chunk of the reference article) to the ‘Text Referencing The Reference Article’ (which cites the reference article). Identify which parts of the ‘Reference Article Text’ are being cited, referenced, or opposed by the ‘Text Referencing The Reference Article.’

    By ‘citing’ or ‘referencing,’ we mean that the ‘Text Referencing The Reference Article’ refers to, aligns with, or supports the information, facts, or concepts in the ‘Reference Article Text.’ The match can be direct, paraphrased, or conceptually similar.

    By ‘opposing,’ we mean that the ‘Text Referencing The Reference Article’ provides a viewpoint or information that contradicts or challenges the information in the ‘Reference Article Text.’

    Guidelines:

        •	For cited or referenced parts: Extract ALL relevant parts of the ‘Reference Article Text’ (chunk) that is being referenced in the ‘Text Referencing The Reference Article.’ You may output the whole ‘Reference Article Text’ (chunk) if the whole chunk is relevant. Start the output with 'Support:' if the ‘Text Referencing The Reference Article’ supports or references the ‘Reference Article Text.’
        •	For opposing parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are being opposed by the ‘Text Referencing The Reference Article.’ Focus on portions where the concepts or facts contradict the information provided. Start the output with 'Oppose:' if the ‘Text Referencing The Reference Article’ opposes the ‘Reference Article Text.’
        •	The match or opposition does not need to be exact; it can be a paraphrased or conceptually aligned or opposing statement.
        •	Consider not only direct references but also cases where the ‘Text Referencing The Reference Article’ discusses related facts or concepts in different wording.
        •	If no part of the ‘Reference Article Text’ is cited or opposed, respond with ‘no.’

    Important Note:
    There might be cases where the phrasing between the ‘Reference Article Text’ and the ‘Text Referencing The Reference Article’ differs, but the underlying concepts are aligned (for references) or contradictory (for opposition). For example:

        •	If the ‘Reference Article Text’ discusses gas production due to bacterial fermentation of lactose and the ‘Text Referencing The Reference Article’ discusses bloating and flatulence after lactose ingestion, these are conceptually aligned, and the relevant portion from the ‘Reference Article Text’ should be extracted, starting with 'Support:'
        •	If the ‘Reference Article Text’ supports the idea that lactose intolerance causes significant symptoms, but the ‘Text Referencing The Reference Article’ argues that lactose intolerance is not as widespread or impactful, then the opposing portion should be extracted, starting with 'Oppose:'

    Example of Supporting Case:

    Input:
    ’Reference Article Text: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Lactose intolerance. Lactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI). However, the two must not be confused, and the causes of symptoms must be considered separately. Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).

    Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.’

    Output:
    'Support: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).’

    Example of Opposing Case:

    Input:
    ’Reference Article Text: Lactose intolerance affects around 70 percent of the global population, causing a range of digestive issues that reduce quality of life for those affected.

    Text Referencing The Reference Article: Recent studies show that lactose intolerance affects only a small proportion of the world, and many people who believe they are lactose intolerant can consume dairy without significant symptoms.’

    Output:
    'Oppose: Lactose intolerance affects around 70 percent of the global population, causing a range of digestive issues that reduce quality of life for those affected.’

    Example of Non-Matching Case (When to Respond with ‘No’):

    Input:
    ’Reference Article Text: Lactase persistence is common among populations of Northern European descent. The LCT −13’910:C/C genotype is associated with the ability to digest lactose in adulthood.

    Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.’

    Output:
    ‘no’

    Output ONLY the quoted texts after Output: in examples shown.
    """
    pro_w_confidence="""

    Compare the ‘Reference Article Text’ (which is a chunk of the reference article) to the ‘Text Referencing The Reference Article’ (which cites the reference article). Identify which parts of the ‘Reference Article Text’ are being cited, referenced, or opposed by the ‘Text Referencing The Reference Article.’ Additionally, assign a confidence score (0-100) to each comparison and place it in brackets next to ‘Support’ or ‘Oppose’ if any part of the text 'Support' or 'Oppose' the ‘Text Referencing The Reference Article’.

    By ‘citing’ or ‘referencing,’ we mean that the ‘Text Referencing The Reference Article’ refers to, aligns with, or supports the information, facts, or concepts in the ‘Reference Article Text.’ The match can be direct, paraphrased, or conceptually similar.

    By ‘opposing,’ we mean that the ‘Text Referencing The Reference Article’ provides a viewpoint or information that contradicts or challenges the information in the ‘Reference Article Text.’

    Guidelines:

        1.	For cited or referenced parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are referenced. Start with ‘Support ([Confidence Score]):’.
        2.	For opposing parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are opposed. Start with ‘Oppose ([Confidence Score]):’.
        3.	Provide Justifications: For each confidence score, give a brief reason explaining the score (e.g., strong conceptual alignment, partial overlap, or weak opposition).
        4.	If no match exists, respond with ‘no’.

    Example Outputs with Confidence Scores:

    Supporting Example:
    Input:
    'Reference Article Text: Bacterial fermentation of lactose produces gases like hydrogen, methane, and CO2, impacting GI function.'
    'Text Referencing The Reference Article: Fermentation of lactose in the gut leads to gas production, causing bloating.'
    Output:
    'Support (90): Bacterial fermentation of lactose produces gases like hydrogen, methane, and CO2, impacting GI function.'


    Opposing Example:
    Input:
    'Reference Article Text: “Lactose intolerance affects around 70 percent of the population.'
    'Text Referencing The Reference Article: “Recent studies indicate lactose intolerance affects a small proportion of the population.'
    Output:
    'Oppose (85): Lactose intolerance affects around 70 percent of the population.'


    Non-Matching Case:
    Input:
    'Reference Article Text: “Lactase persistence is common among Northern Europeans.'
    'Text Referencing The Reference Article: “Fermentation of lactose produces gas.'
    Output:
    'no'

    Output ONLY the quoted texts after Output: in examples shown.
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




async def keyword_search_async(text):

    #original
    kws1="What are the keywords in the Text? Take note these keywords will be used for a graph search in semantic scholar. Output the keywords ONLY."
    #Making keywords a focus on main topic - idea is to narrow down focus - more accurate papers returned
    kws2= f"""
    What are the main topics in the Text? Take note that these topics will be used as keywords for keyword searching. Output the topics as keywords and ONLY output the keywords with them being separated by commas if there are more than one keyword.
    """
    #Approach 2
    kws3="""What are the main topics in the text? The topics should be used as keywords for keyword searching. Output the topics as keywords and only output the keywords as a list. If certain topics are closely related, group them together as a single string inside the main list.

    Rules:

    1. Group closely related topics (e.g., "prebiotics" and "probiotics") into a single string like 'prebiotics, probiotics'.
    2. If a topic stands on its own (e.g., "lactose tolerance"), list it separately.
    3. Always format the output as a single list of strings.
    Example: Text: "A proportion of the world’s population is able to tolerate lactose as they have a genetic variation that ensures they continue to produce sufficient quantities of the enzyme lactase after childhood."
    Output: ['lactose tolerance', 'genetic variation, enzyme lactase', 'lactose tolerance, childhood']
    """
    #Approach 3
    kws4="""
    What are the keywords in terms of topics for the Text? Use the keywords to write keyword searches based on the keywords identified from the Text. Combine keywords if you think they relate to each other. 
    Output the keyword searches as a list of strings ONLY in the format: ['lactase activity restoration', 'lactase activity recovery', ...]
    """
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": kws4},
            {"role": "user", "content": [{"type": "text", "text": f"Text:{text}" }]}
            #{"role": "user", "content": [{"type": "text", "text": kws2}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content.lower()




# Get the references and the cited articles' names in the main article
async def get_references_async(text):
    ref_prompt="In the following text, what are the full texts of each reference (can be multiple sentences), the name of the reference articles, the year the articles were published and the author(s) of the articles? Format your response in this manner:[['The lactase activity is usually fully or partially restored during recovery of the intestinal mucosa.','Lactose intolerance in infants, children, and adolescents','2006','Heyman M.B' ],...]"
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": ref_prompt},
            {"role": "user", "content": [{"type": "text", "text": text }]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content




rerank_support="""You are a semantic ranker. You rank the list according to how much the text in the list support the text for comparison. By support, we mean that the Text for comparison refers to, aligns with, or supports the information, facts, or concepts in the text in the list. The match can be direct, paraphrased, or conceptually similar.
        You output the rank of the list as a list of indexes ONLY."""
async def rerank_support_async(text,list):
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": rerank_support},
            {"role": "user", "content": [{"type": "text", "text": f"Text for comparison: {text}. List: {list}"}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content



rerank_oppose="""You are a semantic ranker. You rank the list according to how much the text in the list oppose the text for comparison. By support, we mean that the text for comparison provides a viewpoint or information that contradicts or challenges the information in the text in the list.
        You output the rank of the list as a list of indexes ONLY."""
async def rerank_oppose_async(text,list):
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": rerank_oppose},
            {"role": "user", "content": [{"type": "text", "text": f"Text for comparison: {text}. List: {list}"}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content