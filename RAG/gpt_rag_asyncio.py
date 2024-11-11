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
        az_path = os.getenv("az_path", "az")
        result = subprocess.run(
            [az_path, 'account', 'get-access-token', '--resource', 
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

#retriever and siever for new reference (with classification)
async def call_retrieve_sieve_with_async(chunk, ref):
    await initialize_client()
    return await async_retry_on_exception(retriever_and_siever_async, chunk, ref)

#retriever and siever for sanity checking (no classification)
async def call_retrieve_sieve_with_async_check(chunk, ref):
    await initialize_client()
    return await async_retry_on_exception(retriever_and_siever_async_check, chunk, ref)

# Keyword search function
async def call_keyword_search_async(text, prompt=None):
    await initialize_client()
    result = await async_retry_on_exception(keyword_search_async, text, prompt)
    return result
#Get the statements, reference article titles, authors of reference articles and year reference articles released
async def call_get_ref_async(text):
    await initialize_client()
    result = await async_retry_on_exception(get_references_async, text)
    return result

#agent to regenerate prompt for better keyword generation
async def call_rewritter_async(prompt):
    await initialize_client()
    result = await async_retry_on_exception(rewritter, prompt)
    return result

# agent to select best prompt from db
async def call_selector_async(list_of_prompts):
    await initialize_client()
    result = await async_retry_on_exception(selector, list_of_prompts)
    return result

#
async def call_summarizer_scorer_async(list_of_sieved_chunks,statement,sentiment):
    result=await async_retry_on_exception(summarizer_scorer,list_of_sieved_chunks,statement,sentiment)
    return result

# support or oppose included, used to classify the new ref
# Classification included
async def retriever_and_siever_async(chunk, ref):
    pro_w_confidence="""

    Compare the ‘Reference Article Text’ (which is a chunk of the reference article) to the ‘Text Referencing The Reference Article’ (which cites the reference article). Identify which parts of the ‘Reference Article Text’ are being cited, referenced, or opposed by the ‘Text Referencing The Reference Article.’ Additionally, assign a confidence score (0-100) to each comparison and place it in brackets next to ‘Support’ or ‘Oppose’ if any part of the text 'Support' or 'Oppose' the ‘Text Referencing The Reference Article’.

    By ‘citing’ or ‘referencing,’ we mean that the ‘Text Referencing The Reference Article’ refers to, aligns with, or supports the information, facts, or concepts in the ‘Reference Article Text.’ The match can be direct, paraphrased, or conceptually similar.

    By ‘opposing,’ we mean that the ‘Text Referencing The Reference Article’ provides a viewpoint or information that contradicts or challenges the information in the ‘Reference Article Text.’

    Guidelines:

        1.	For cited or referenced parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are referenced. Start with ‘Support ([Confidence Score]):’.
        2.	For opposing parts: Extract ALL relevant parts of the ‘Reference Article Text’ that are opposed. Start with ‘Oppose ([Confidence Score]):’.
        3.	If no match exists, respond with ‘no’.

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

    Output ONLY the extraction. (the quoted texts after Output: in examples shown).
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

#no support or oppose classification (for sanity checking)
async def retriever_and_siever_async_check(chunk, ref):
    pro = """
    Compare the 'Reference Article Text' (which is a chunk of the reference article) to the 'Text Referencing The Reference Article' (which cites the reference article). Identify which parts of the 'Reference Article Text' are being cited or referenced by the 'Text Referencing The Reference Article.' Referencing The Reference Article’ (which cites the reference article). Additionally, assign a confidence score (0-100) to each comparison and place it in brackets at the start of the output based on how likely 'Text Referencing The Reference Article' cites the 'Reference Article Text'.

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
    '(90) Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).'

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




async def keyword_search_async(text, prompt=None):

    
    #Approach 3
    kws4="""
    What are the keywords in terms of topics for the Text? Use the keywords to write keyword searches based on the keywords identified from the Text. Combine keywords if you think they relate to each other. 
    Output the keyword searches as a list of strings ONLY in the format: ['lactase activity restoration', 'lactase activity recovery', ...]
    """
    if prompt is None:
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
    else:
        data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": prompt},
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




async def rewritter(old_prompt):
    retry_prompt="""
    You are an advanced prompt-tuning agent. Your task is to craft a new, improved prompt to extract precise and meaningful keywords from text-based statements. Below is the old prompt I used, which did not perform well:
    OLD_PROMPT:
    {old_prompt}
    Your new prompt should outperform the old one by being clearer, more specific, and more aligned with the task objective. Focus on improving the clarity and specificity, reducing ambiguity, and ensuring that the extracted keywords are concise and representative of the key concepts. Include any necessary constraints, instructions, or formatting rules to improve the output.

    Here are guidelines for the new prompt:

        1.	Goal: The new prompt should ensure keywords capture the essence of the statements, focusing on nouns, named entities, and concepts central to the meaning.
        2.	Style/Tone: Make it precise and instruction-driven.
        3.	Constraints: If helpful, specify the number of keywords, exclude generic words, and ensure uniqueness in the results.
        4.	Output Format: Ensure the keywords are listed or returned in a readable and structured format.

    Your task: Generate the new improved prompt with these improvements in mind. The new prompt should replace or build upon the old one. ONLY OUTPUT THE NEWLY GENERATED PROMPT AND NOTHING ELSE""".format(old_prompt=old_prompt)
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": 'You are an advanced prompt tuning agent. You output only the tuned prompt and nothing else.'},
            {"role": "user", "content": [{"type": "text","text": retry_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content



#make sure list of prompt is a string first
async def selector(list_of_prompts):
    selector_prompt="""
    You are a specialized evaluator agent tasked with selecting the best prompt for generating high-quality keywords from text-based statements. Your job is to review a list of prompts and choose the one most aligned with the following criteria:

    List of prompts: {list_of_prompts}

    Here are guidelines for the selecting the best prompt:

        1. **Clarity and Specificity:** The prompt should clearly instruct the model to extract relevant keywords. Look for any elements that remove ambiguity and make the instructions straightforward.
        
        2. **Keyword Focus:** Ensure the prompt guides the model to capture essential concepts, focusing on nouns, named entities, and core ideas central to the statement's meaning.

        3. **Constraints and Instructions:** The prompt should, where useful, include constraints on keyword quantity, discourage generic terms, and specify uniqueness in keywords, enhancing relevance.

        4. **Format Requirements:** The selected prompt should direct the output to be structured in a clear, readable format for easy keyword identification.

    Only output the best prompt from the list that excels in these criteria, ensuring it achieves the stated objective effectively.""".format(list_of_prompts=list_of_prompts)

    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": 'You are an advanced evaluation agent specialized in prompt selection. Your role is to evaluate a list of provided prompts and select only the best one based on clarity, focus on essential keywords, appropriate constraints, and structured format requirements. Output only the selected best prompt and nothing else.'},
            {"role": "user", "content": [{"type": "text","text": selector_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content


async def summarizer_scorer(list_of_sieved_chunks,statement,sentiment):
    if sentiment=='support': 
        summarizer_prompt_support="""
        You are an expert summarizer and evaluator. Your role is to help determine whether a single paper provides strong support for a specific statement based on all its excerpts.

        Instructions:

        Summarize the Key Idea of All Excerpts: Summarize the overall message conveyed by the excerpts in relation to the statement. Focus on how these excerpts support or strengthen the statement’s validity.

        Use Original Text: In the summary, include the EXACT original text from the excerpts in square brackets [ ] for direct reference.

        Provide an Overall Assessment:

        strongly support: The paper provides strong support for the statement.
        Meh: The paper offers limited or only partially relevant support for the statement.
        oppose: The paper actually opposes the statement rather than supporting it.
        Output Format:

        Summarize all excerpts concisely.
        End with the assessment score in brackets (e.g., (strongly support), (Meh), or (oppose)).
        Only output the summary and the score.

        Input:

        Statement: {statement}
        List of Excerpts: {list_of_sieved_chunks}
        """.format(list_of_sieved_chunks=list_of_sieved_chunks,statement=statement)

        system_prompt_support="""
        You are an expert evaluator and summarizer focused on determining the alignment of research excerpts with a specific statement. Each excerpt you receive is from the same paper, and your job is to evaluate whether the paper, as a whole, provides strong support, partial support, or opposition to the statement.

        Your Task:
        Summarize the Overall Key Ideas: Based on all excerpts provided, summarize the main ideas in relation to the statement. Look for points that directly support or challenge the statement and highlight these in your summary.

        Use Exact Text: For accuracy, use the EXACT original text from the excerpts in square brackets [ ] within your summary. This direct referencing allows others to see the basis for your conclusions.

        Provide a Final Assessment:

        strongly support: If the paper provides strong, direct evidence in favor of the statement.
        Meh: If the paper provides only limited or partially relevant support for the statement.
        oppose: If the paper actually provides evidence against the statement rather than supporting it.
        Format:
        Summarize the key ideas concisely, directly referencing excerpts with square brackets [ ].
        End with a final assessment in parentheses, using (strongly support), (Meh), or (oppose).
        Be Concise and Objective:
        Focus on how effectively the excerpts align with the statement.
        Avoid adding extra interpretation beyond the given instructions.
        Only output the summary and the score.
        """

        data={
            "model":"gpt-4o",
            "messages":[
                {"role": "system", "content": system_prompt_support},
                {"role": "user", "content": [{"type": "text","text": summarizer_prompt_support}]}
            ],
            "temperature":0
        }
        response = await async_client.chat.completions.create(**data)
    else:
        summarizer_prompt_oppose="""
        You are an expert summarizer and evaluator. Your role is to help determine whether a single paper provides strong opposition to a specific statement based on all its excerpts.

        Instructions:

        Summarize the Key Idea of All Excerpts: Summarize the overall message conveyed by the excerpts in relation to the statement. Focus on how these excerpts challenge or contradict the statement’s validity.

        Use Original Text: In the summary, include the EXACT original text from the excerpts in square brackets [ ] for direct reference.

        Provide an Overall Assessment:

        strongly oppose: The paper provides strong opposition to the statement.
        Meh: The paper offers limited or only partially relevant opposition to the statement.
        support: The paper actually supports the statement rather than opposing it.
        Output Format:

        Summarize all excerpts concisely.
        End with the assessment score in brackets (e.g., (strongly oppose), (Meh), or (support)).
        Only output the summary and the score.

        Input:

        Statement: {statement}
        List of Excerpts: {list_of_sieved_chunks}
        """.format(list_of_sieved_chunks=list_of_sieved_chunks,statement=statement)
        system_prompt_oppose="""
        You are an expert evaluator and summarizer focused on determining whether a single paper provides strong opposition to a specific statement based on its excerpts. Each excerpt you receive is from the same paper, and your job is to assess whether the paper effectively contradicts or challenges the statement.

        Your Task:
        Summarize the Overall Key Ideas: Based on all excerpts provided, summarize the main ideas in relation to the statement. Focus on points that directly challenge, contradict, or provide counter-evidence to the statement and highlight these in your summary.

        Use Exact Text: For accuracy, use the EXACT original text from the excerpts in square brackets [ ] within your summary. This allows others to see the basis for your conclusions.

        Provide a Final Assessment:

        strongly oppose: If the paper provides strong, direct evidence that contradicts or opposes the statement.
        Meh: If the paper provides only limited or partially relevant opposition to the statement.
        support: If the paper actually provides evidence in favor of the statement rather than opposing it.
        Format:
        Summarize the key ideas concisely, directly referencing excerpts with square brackets [ ].
        End with a final assessment in parentheses, using (strongly oppose), (Meh), or (support).
        Be Concise and Objective:
        Focus on how effectively the excerpts oppose the statement.
        Avoid adding extra interpretation beyond the given instructions.
        Only output the summary and the score.

        """
        data={
            "model":"gpt-4o",
            "messages":[
                {"role": "system", "content": system_prompt_oppose},
                {"role": "user", "content": [{"type": "text","text": summarizer_prompt_oppose}]}
            ],
            "temperature":0
        }
        response = await async_client.chat.completions.create(**data)


    return response.choices[0].message.content