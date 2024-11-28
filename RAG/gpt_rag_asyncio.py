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

# summarize and score according to relevance, detects wrong sentiment as well
async def call_summarizer_scorer_async(list_of_sieved_chunks,statement,sentiment):
    result=await async_retry_on_exception(summarizer_scorer,list_of_sieved_chunks,statement,sentiment)
    return result
#extracts info from main .txt to prep for edits
async def call_extract_to_edit_async(file_content):
    result=await async_retry_on_exception(extract_to_edit,file_content)
    return result

#replace old w new citations
async def call_extract_statement_citation(text,new_statements):
    result=await async_retry_on_exception(extract_statement_citation,text,new_statements)
    return result

"""Edit final text prompts"""
#Converts the final df to an output to replace the text w regex
async def call_convert_to_replace(row,text):
    result=await async_retry_on_exception(convert_to_replace,row,text)
    return result

#Locate which text in list of text contains the statement and citation and edit accordingly
async def call_find_to_edit_statement(text,list_statement):
    result=await async_retry_on_exception(find_to_edit_statement,text,list_statement)
    return result

#Locate reference list from text for removal
async def call_find_reference_list(text):
    result=await async_retry_on_exception(find_reference_list,text)
    return result

#Edit the reference list
async def call_replace_reference_list(reference_list,remove_list,add_list):
    result=await async_retry_on_exception(replace_reference_list,reference_list,remove_list,add_list)
    return result
#extract citations
async def call_citation_extractor(whole_statement):
    result=await async_retry_on_exception(citation_extractor,whole_statement)
    return result

#create citations behind edits
async def call_edit_citationer(row,text):
    result=await async_retry_on_exception(edit_citationer,row,text)
    return result


#append edits with citations behind statements
async def call_add_edits(list,text):
    result=await async_retry_on_exception(add_edits,list,text)
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
        4.  If the ‘Reference Article Text’ is a citation, no matter the classification, give it a score lower than 70

    Example Outputs with Confidence Scores:

    Supporting Example:
    Input:
    'Reference Article Text: Bacterial fermentation of lactose produces gases like hydrogen, methane, and CO2, impacting GI function.'
    'Text Referencing The Reference Article: Fermentation of lactose in the gut leads to gas production, causing bloating.'
    Output:
    'Support (90): Bacterial fermentation of lactose produces gases like hydrogen, methane, and CO2, impacting GI function.'

    Supporting Example but is citation:

    Input:
    'Reference Article Text: Improvement of lac-tose digestion by humans following ingestion of unfermented aci-dophilus milk: inﬂuence of bile sensitivity, lactose transport, andacid tolerance of Lactobacillus acidophilus.Journal of Dairy Science80 (8):1537–1545.Odamaki, T., H.Sugahara, and S.Yonezawa. 2012.Effect of the oral intakeof yogurt containing Biﬁdobacterium longum BB536 on the cell num-bers of enterotoxigenic Bacteroides fragilis in microbiota.Anaerobe 18(1):14–18.Ojetti, V., G.Gigante, and M.Gabrielli. 2010.The effect of oral supplemen-tation with Lactobacillus reuteri or tilactase in lactose intolerantpatients: randomized trial.European Review for Medical and Pharma-cological Sciences 14 (3):163–70.Pakdaman, M.N., J.K.Udani, J.P.Molina, and M.Shahani. 2016.
    Text Referencing The Reference Article: Pre- and probiotics may have a positive effect on lactose tolerance.'

    Output:
    'Support (60) improvement of lactose digestion by humans following ingestion of unfermented acidophilus milk: influence of bile sensitivity, lactose transport, and acid tolerance of lactobacillus acidophilus.'
    
    Opposing Example:
    Input:
    'Reference Article Text: “Lactose intolerance affects around 70 percent of the population.'
    'Text Referencing The Reference Article: “Recent studies indicate lactose intolerance affects a small proportion of the population.'
    Output:
    'Oppose (85): Lactose intolerance affects around 70 percent of the population.'

    Opposing Example but is citation:

    Input:
    'Reference Article Text: Dig.Dis. 2018, 36, 271–280. [CrossRef] [PubMed]30.Triggs, C.M.; Munday, K.; Hu, R.; Fraser, A.G.; Gearry, R.B.; Barclay, M.L.; Ferguson, L.R.Dietary factors in chronic inﬂammation:Food tolerances and intolerances of a New Zealand Caucasian Crohn’s disease population.Mutat.Res. 2010, 690, 123–138.[CrossRef]31.Labayen, I.; Forga, L.; Gonzalez, A.; Lenoir-Wijnkoop, I.; Nutr, R.; Martinez, J.A.Relationship between lactose digestion, gastroin-testinal transit time and symptoms in lactose malabsorbers after dairy consumption.Aliment.Pharmacol.Ther. 2001, 15, 543–549.[CrossRef] [PubMed]32.Pelletier, X.; Laure-Boussuge, S.; Donazzolo, Y.Hydrogen excretion upon ingestion of dairy products in lactose-intolerant malesubjects:
    Text Referencing The Reference Article: A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhoea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance.
    Output:
    'Oppose (60) relationship between lactose digestion, gastroin-testinal transit time and symptoms in lactose malabsorbers after dairy consumption.'

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
    - If the ‘Reference Article Text’ is a citation, no matter the classification, give it a score lower than 70

    Important Note:
    There might be cases where the phrasing between the 'Reference Article Text' and the 'Text Referencing The Reference Article' differs, but the underlying concepts are aligned. For example, if the 'Reference Article Text' discusses gas production due to bacterial fermentation of lactose and the 'Text Referencing The Reference Article' discusses bloating and flatulence after lactose ingestion, these are conceptually aligned, and the relevant portion from the 'Reference Article Text' should be extracted.

    Example of Matching Case:

    Input:
    'Reference Article Text: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Lactose intolerance. Lactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI). However, the two must not be confused and the causes of symptoms must be considered separately. Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).

    Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

    Output:
    '(90) Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).'

    Example of Matching Case but is citation:

    Input:
    'Reference Article Text: Improvement of lac-tose digestion by humans following ingestion of unfermented aci-dophilus milk: inﬂuence of bile sensitivity, lactose transport, andacid tolerance of Lactobacillus acidophilus.Journal of Dairy Science80 (8):1537–1545.Odamaki, T., H.Sugahara, and S.Yonezawa. 2012.Effect of the oral intakeof yogurt containing Biﬁdobacterium longum BB536 on the cell num-bers of enterotoxigenic Bacteroides fragilis in microbiota.Anaerobe 18(1):14–18.Ojetti, V., G.Gigante, and M.Gabrielli. 2010.The effect of oral supplemen-tation with Lactobacillus reuteri or tilactase in lactose intolerantpatients: randomized trial.European Review for Medical and Pharma-cological Sciences 14 (3):163–70.Pakdaman, M.N., J.K.Udani, J.P.Molina, and M.Shahani. 2016.
    Text Referencing The Reference Article: Pre- and probiotics may have a positive effect on lactose tolerance.'

    Output:
    '(60) improvement of lactose digestion by humans following ingestion of unfermented acidophilus milk: influence of bile sensitivity, lactose transport, and acid tolerance of lactobacillus acidophilus.'

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
        You are an expert summarizer and evaluator. Your role is to help determine whether a single paper is relevant in terms of providing support for a specific statement based on all its excerpts.
        By  'support' or ‘citing’ or ‘referencing,’ we mean that the ‘Text Referencing The Reference Article’ refers to, aligns with, or supports the information, facts, or concepts in the ‘Reference Article Text.’ The match can be direct, paraphrased, or conceptually similar.

        Instructions:

        Summarize the Key Idea of All Excerpts: Summarize the overall message conveyed by the excerpts in relation to the statement. Focus on how these excerpts support or strengthen the statement’s validity.

        Use Original Text: In the summary, include the EXACT original text from the excerpts in square brackets [ ] for direct reference.

        Provide an Overall Assessment:

        Relevant: The paper is relevant in providing support for the statement.
        Irrelevant: The paper is not relevant in supporting the statement (irrelevance to the statement)
        Oppose: The paper actually opposes the statement, which in this case the sentiments of the extracts are identified wrongly
        Output Format:

        Summarize all excerpts concisely.
        End with the assessment score in brackets () (e.g., (Relevant), (Irrelevant), or (Oppose)).
        Output the summary and the score in brackets () ONLY.

        Example of Oppose (to let you know what constitues as wrong classification)

        Input:
        Statement: 'A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhoea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance.'
        List of Excerpts that opposes the statement: 
        '['Objective:To assess the clinical characteristics of Lactose intolerance (LI) as well as its relationship with demographic factors among diarrheal children below ïve years of age.Methods:A cross sectional study was conducted enrolling 50 diarrheal patients in equal proportion by gender.The present study was conducted over children suffering from profuse diarrhea admitted to the Pediatrics ward at LUMHS and CIVIL hospital Hyderabad, Pakistan during July 2018 to January 2019.The questionnaire-based analysis was conducted to gather information regarding dietary index and manifestation of symptoms after milk consumption.Clinical analysis was performed using lactose tolerance test, Stool pH and reducing substance respectively.The obtained results were analyzed using SPSS.Results: 20 children were found to be suffering from lactose intolerance.', 'The clinical symptoms observed among individuals affected by LI included loose motion, weight loss, abdominal distention, and the presence of pus cells in stool indicating the signs of infection.T-test showed statistical signiïcance (p-value < 0.05) over physical attributes such as height and number of pus cells among LI patients as compared to lactose tolerant (LT) patients.The ïnding of pus cells in the stool simultaneous to the strong statistical correlation between relieve in symptoms with increasing age also aírmed the existence of secondary type hypo-lactasia.The study also highlighted the demographic aspects contributing to the prevalence of the condition.Conclusions:Secondary lactose intolerance was found with shortened heights of patients and increased number of pus cells in stool.VOL. 05, ISSUE. 06 JUNE 2022Keywords:Lactose Intolerance, Diarrhea, Gut Health, Lactose Tolerance Test, Lactase*Corresponding Author:', 'Clinical Assessment and Demographic Insights of Lactose Intolerance Among Diarrheal Children at Hyderabad, Pakistan:Lactose Intolerance Among Diarrheal Children .Pakistan BioMedical Journal, 7(02). https://doi.org/10.54393/ pbmj.v7i02.1030Yousuf M et al.,  DOI: https://doi.org/10.54393/pbmj.v7i02.1030Lactose Intolerance Among Diarrheal ChildrenText on page 2:(commonly known as adult lactose intolerance) is characterized as a condition where the patients present normal lactose expression after birth, which gradually declines during growing up.On the other hand, secondary lactose intolerance may develop in a person with a healthy small intestine during episodes of acute illness causing mucosal damage or from medications resulting from certain gastrointestinal disease.This type of lactose intolerance can occur in both infants and adults and is generally reversible [5].A number of methods have been reported to assess the degree of lactose intolerance such as the hydrogen breath test, the milk tolerance test, and diet elimination protocol reducing sugar and stool pH detection test [6-8].', 'The value of n was calculated as 48.98 or ~ 49.Children suffering from any organic disease (chicken pox, measles etc.) were excluded from the study.We also excluded children already taking lactose free diet from our study so as to avoid bias in results of the study.The study was designed based on the data obtained in the form of a questionnaire along with the clinical samples collected over the period of time.The study was conducted with the ethical approval of the ethical committee on 15-10-2018 at the Institute of Biochemistry, University of Sindh (Jamshoro) with a reference number IOB/125/2018.The patients were categorized into two groups Lactose tolerant (LT) and Lactose Intolerant (LI).In both groups the patients suffered from mild to severe diarrhea, however, the patients classiïed in LI group showed recurrence of symptoms after diet elimination protocol and lactose tolerance test.On the contrary, the patients in the LT group showed no such outcome.For lactose tolerance test, patients were allowed to ingest 500 mL approx. of lactose-containing milk followed by the measurement of their blood glucose levels prior to and later to the ingestion [9].', 'PBMJ, Published by Crosslinks International PublishersPBMJ VOL. 7 Issue. 2 February 2024Yousuf M et al.,  DOI: https://doi.org/10.54393/pbmj.v7i02.1030Lactose Intolerance Among Diarrheal ChildrenText on page 3:Table 1:Comparative analysis of blood glucose levels prior (baseline) and after the ingestion of lactose at different time intervals between LI and LT group. test and the p-values obtained among LI and LT patients after 30 and 60 minutes.The glycemic index (glucose levels) showed signiïcant correlation between two groups LI and LT after the intake of milk in comparison to baseline.This showed that glycemic index can be accounted as a reliable parameter in the assessment of lactose intolerance.Mean ± SDMean ± SDLT (Lactose atdifferent time intervals)Baseline96.5 ± 16.3139.8 ± 26.2134.8 ± 35.492.9 ± 12.40.330.0000170.00005105.8 ± 15.84101.4 ± 12.24Variablesp –valueLI(Lactose intolerant)Mean ± SD30 minutes60 minutesPresence of reducing sugar in stool was tested to categorize patients in two groups i-e lactose tolerant and lactose intolerant.', 'Based on the test results, out of 50 patients, 17 patients were diagnosed as lactose intolerant.However, 03 patients showed negative results despite of the persistent symptoms of LI (Figure 1).Figure 1:Prevalence of lactose intolerance on basis of fecal reducing substance.Upon measurement of the stool pH of ïfty patients, we found that the ones conïrmed as lactose intolerant had a slightly acidic pH (5.5 - 5.9) compared to the lactose tolerant (7.0 – 7.5) patients.Moreover, in our assessment, the most prevalent symptoms observed in the LI case included Loose motion (L/M) with mucus, weight loss, vomiting and abdominal distention.The statistical analysis indicated a signiïcant relationship between the LI condition and the height (L) and the number of pus cells (pc) found in the stool of the affected LI patients in comparison to lactose tolerant patients (Figures 2a-c).The obtained p-values were 0.03, 0.08, and 0.01 for height, body mass and the number of pus cells, respectively.Figure 2:Statistical signiïcance of physiological parameters2a:', 'Length, 2b:Mass and 2c:Presence of pus cells among LI and LT patients, respectively. p-value < 0.05 was considered as signiïcant.42Copyright © 2024.PBMJ, Published by Crosslinks International PublishersPBMJ VOL. 7 Issue. 2 February 2024Fecal reducing testLactose tolerantLactose IntolerantAnomalies30173Boxplot of LI length, LT length 1009080706050DataLILLTL(a)98765432Boxplot of LI Mass, LT MassDataLI MassLT Mass(b)20151050DataBoxplot of PC LI, PC LTpc LIpc LT(c)Yousuf M et al.,  DOI: https://doi.org/10.54393/pbmj.v7i02.1030Lactose Intolerance Among Diarrheal ChildrenText on page 4:C O N C L U S I O N SThe current study aimed to understand the clinical and demographic attributes among patients suffering from hypo-lactasia.The common symptoms included vomiting, abdominal distension, loose motion, and weight loss accompanied by the release of mucus in the stool of LI patients.The children suffering from such intolerance had shortened height and may present an increased number of pus cells in stool.', 'Catanzaro R, Sciuto M, Marotta F.Lactose intolerance:An update on its pathogenesis, diagnosis, and treatment.Nutrition Research. 2021 May; 89: 23-34. doi: 10.1016/j.nutres.2021.02.003.Robles L and Priefer R.Lactose intolerance:What your breath can tell you.Diagnostics. 2020 Jun; 10(6): 412. doi: 10.3390/diagnostics10060412.Heyman MB.Committee on Nutrition.Lactose intolerance in infants, children, and adolescents.Pediatrics. 2006 Sep; 118(3): 1279-86. doi: 10.1542/ peds.2006-1721.Beyerlein L, Pohl D, Delco F, Stutz B, Fried M, Tutuian R.Correlation between symptoms developed after the oral ingestion of 50 g lactose and results of hydrogen breath testing for lactose intolerance.Alimentary Pharmacology and Therapeutics. 2008 Apr; 27(8): 659-65. doi: 10.1111/j.1365-2036.2008. 03623.x.']'
        Output: 
        'The excerpts collectively highlight the clinical symptoms and diagnostic methods for lactose intolerance, emphasizing the reliability of clinical symptoms and self-reporting in diagnosing the condition. Key points include:

        1. Clinical symptoms such as "loose motion, weight loss, abdominal distention, and the presence of pus cells in stool" are significant indicators of lactose intolerance [The clinical symptoms observed among individuals affected by LI included loose motion, weight loss, abdominal distention, and the presence of pus cells in stool indicating the signs of infection].
        2. The study used various diagnostic methods, including the lactose tolerance test, stool pH, and reducing substance tests, to confirm lactose intolerance [Clinical analysis was performed using lactose tolerance test, Stool pH and reducing substance respectively].
        3. The presence of symptoms like "vomiting, abdominal distension, loose motion, and weight loss" was consistently observed in lactose intolerant patients [The common symptoms included vomiting, abdominal distension, loose motion, and weight loss accompanied by the release of mucus in the stool of LI patients].
        4. The study found a significant correlation between clinical symptoms and lactose intolerance, suggesting that these symptoms are reliable indicators [The statistical analysis indicated a significant relationship between the LI condition and the height (L) and the number of pus cells (pc) found in the stool of the affected LI patients in comparison to lactose tolerant patients].
        (Oppose)'
        Explanation: In this case, the chunks and hence summary oppose the idea of the statement where self reported and clinical diagnosis are unreliable in diagnosis of lactose intolerance and in fact it says they are reliable, which is what the statement is NOT taking about.

        Example of Relevant

        Input:
        Statement: 'A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhoea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance.'
        List of Excerpts that opposes the statement: 
        '['!The Author 2010.Published by Oxford University Press on behalf of the Association of Physicians.All rights reserved.For Permissions, please email: journals.permissions@oxfordjournals.orgQ J Med 2010; 103:555–572doi:10.1093/qjmed/hcq082Advance Access Publication 3 June 2010 by guest on October 13, 2011qjmed.oxfordjournals.orgDownloaded from Text on page 3:BackgroundLactose malabsorption is the most common type ofcarbohydrate malabsorption and is caused by lowlactase levels.1 Lactase activity is highest at birthand declines after weaning.The age at which thisdecline starts and the proportion of the adult popula-tion with lactase levels low enough to be consideredhaving ‘hypolactasia’ are both strongly related to eth-nicity, with highest rates of lactose malabsorption inAsian populations, Native Americans and AfricanAmericans (60–100%) and lowest rates in people ofnorthern European origin and the US white popula-tion (2–22%).2 When lactose malabsorption gives riseto symptoms, this is called ‘lactose intolerance’.Although lactose intolerance is often bothersome forpatients, once recognized it may be managed bysimple dietary adjustments.Diagnosing lactose intolerance is not straightfor-ward.', 'Rana SV, Mandal AK, Kochhar R, Katyal R, Singh K.Lactoseintolerance in different types of irritable bowel syndrome innorth Indians.Trop Gastroenterol 2001; 22:202–4.35.Sciarretta G, Giacobazzi G, Verri A, Zanirato P, Garuti G,Malaguti P.Hydrogen breath test quantification and clinicalcorrelation of lactose malabsorption in adult irritable bowelsyndrome and ulcerative colitis.Dig Dis Sci 1984; 29:1098–04.36.SzilagyiA,MalolepszyP,YesovitchS,NathwaniU,Vinokuroff C, Cohen A, et al.Inverse dose effect of pretestdietary lactose intake on breath hydrogen results and symp-toms in lactase nonpersistent subjects.Dig Dis Sci 2005;50:2178–82.37.Tolliver BA, Herrera JL, DiPalma JA.', 'When lactose malabsorption gives riseto symptoms, the result is called ‘lactose intoler-ance’.Although lactose intolerance is often bother-some for patients, once recognized it may bemanaged by simple dietary adjustments.However,diagnosing lactose intolerance is not straightfor-ward, especially in primary care.Aim:To summarize available evidence on the diag-nostic performance of gastrointestinal symptoms andself-reported milk (lactose) intolerance in primarycare, and the relationship between lactose malab-sorption and intolerance.Data sources:', 'GermanEnck, 199024316270.33 (0.08–0.70)0.96 (0.82-1.00)0.75 (0.19–0.99)0.18 (0.07–0.36)Ethnicity: caucasian no vs. yesTolliver, 1994371812291020.38 (0.25–0.54)0.90 (0.82–0.94)0.60 (0.41–0.77)0.22 (0.15–0.30)Gender: female vs. maleDiPalma, 1988221145947220.71 (0.63–0.78)0.27 (0.18–0.38)0.66 (0.58–0.73)0.68 (0.56–0.79)Gender: female vs. maleParker, 20013225608290.76 (0.58–0.89)0.33 (0.23–0.43)0.29 (0.20–0.40)0.22 (0.10–0.38)Gender: female vs. maleSzilagyi, 200536373622230.63 (0.49–0.75)0.39 (0.27–0.53)0.51 (0.39–0.63)0.49 (0.34–0.64)Gender: female vs. maleVernia, 1995391105247210.70 (0.62–0.77)0.29 (0.19–0.41)0.68 (0.60–0.75)0.69 (0.57–0.80)Milk intolerance awareness (yes vs. no)MI awarenessBianchi Porro, 19831932713250.71 (0.56–0.84)0.78 (0.60–0.91)0.82 (0.67–0.93)0.34 (0.20–0.51)Awareness of lactose-associated symptomsDiPalma, 1988224829113520.30 (0.23–0.38)0.64 (0.53–0.75)0.62 (0.51–0.73)0.69 (0.61–0.76)Awareness of food intoleranceEnck, 1988238611120.42 (0.20–0.67)0.67 (0.41–0.87)n.a.n.a.Self-reported MIFarup, 2004252301390.67 (0.09–0.99)0.57 (0.44–0.68)0.06 (0.01–0.21)0.03 (0.00–0.13)Self-reported MIGupta, 200726391743130.48 (0.36–0.59)0.43 (0.26–0.63)0.70 (0.56–0.81)0.77 (0.64–0.87)Self-reported MIMetz, 197530426130.40 (0.12–0.74)0.87 (0.60–0.98)0.67 (0.22–0.96)0.32 (0.13–0.57)Self-reported MIVernia, 2004815249138630.52 (0.47–0.58)0.56 (0.47–0.66)0.76 (0.69–0.81)0.69 (0.62–0.75)Daily milk intake <250 vs. >250 mlBozzani, 1986202421130.69 (0.51–0.83)0.60 (0.15–0.95)0.92 (0.75–0.99)0.79 (0.49–0.95)Milk consumption: no vs. yesSciarretta, 1984354042260.65 (0.51–0.76)0.60 (0.26–0.88)0.91 (0.78–0.98)0.79 (0.59–0.92)Milk consumption: no vs. yesBianchi Porro, 1983a,1932241380.71 (0.56–0.84)0.25 (0.12–0.43)0.57 (0.43–0.70)0.62 (0.38–0.82)Symptoms during and after LHBT (yes vs. no)Symptoms during LHBTBernardes-Silva, 2007172883360.90 (0.74–0.98)0.82 (0.67–0.92)0.78 (0.61–0.90)0.08 (0.02–0.21)Symptoms during LHBTBeyerlein, 200818338463382880.90 (0.86–0.93)0.38 (0.35–0.42)0.42 (0.39–0.46)0.12 (0.08–0.16)Symptoms during LHBTCasellas, 20082176662270.97 (0.91–0.99)0.29 (0.20–0.39)0.54 (0.45–0.62)0.07 (0.01–0.23)– Symptom score during LHBT 7Casellas, 2008a,21603018630.77 (0.66–0.86)0.68 (0.57–0.77)0.67 (0.56–0.76)0.22 (0.14–0.33)Symptoms during LHBTDiPalma, 1988221241331680.80 (0.73–0.860.84 (0.74–0.91)0.91 (0.84–0.95)0.31 (0.22–0.41)Symptoms during LHBT and 24 h thereafterFarup, 2004252261440.67 (0.09–0.99)0.63 (0.51–0.74)0.07 (0.01–0.24)0.02 (0.00–0.12)Symptoms during LHBTFernandez, 200641737190.50 (0.23–0.77)0.86 (0.65–0.97)0.70 (0.35–0.93)0.27 (0.12–0.48)Symptoms during LHBTGupta, 200726482041150.54 (0.43–0.65)0.43 (0.26–0.61)0.71 (0.58–0.81)0.73 (0.60–0.84)Symptoms during LHBTHermans, 199727671628720.89 (0.80–0.95)0.31 (0.25–0.37)0.29 (0.24–0.36)0.10 (0.04–0.19)(continued)Lactose malabsorption and intolerance567 by guest on October 13, 2011qjmed.oxfordjournals.orgDownloaded from Text on page 15:ingestion (sensitivity).', 'Vernia P, Di Camillo M, Marinaro V.Lactose malabsorption,irritable bowel syndrome and self-reported milk intolerance.Dig Liver Dis 2001; 33:234–9.41.Fernandez-Banares F, Rosinach M, Esteve M, Forne M,Espinos JC, Maria VJ.Sugar malabsorption in functionalabdominal bloating: a pilot study on the long-term effect ofdietary treatment.Clin Nutr 2006; 25:824–31.42.Lisker R, Solomons NW, Perez BR, Ramirez MM.Lactase andplacebo in the management of the irritable bowel syndrome:a double-blind, cross-over study.Am J Gastroenterol 1989;84:756–62.43.Bohmer CJ, Tuynman HA.The clinical relevance of lactosemalabsorptioninirritablebowelsyndrome.EurJGastroenterol Hepatol 1996; 8:1013–16.44.BohmerCJ,TuynmanHA.Theeffectofalactose-restricted diet in patients with a positive lactose tolerancetest,earlierdiagnosedasirritablebowelsyndrome:a 5-year follow-up study.Eur J Gastroenterol Hepatol 2001;13:941–4.45.']'

        Output: 
        'The excerpts collectively highlight the complexity and challenges in diagnosing lactose intolerance, particularly through clinical symptoms and self-reporting. They emphasize that while lactose intolerance can be managed through dietary adjustments, diagnosing it is not straightforward. For instance, [“Diagnosing lactose intolerance is not straightforward, especially in primary care”] and [“To summarize available evidence on the diagnostic performance of gastrointestinal symptoms and self-reported milk (lactose) intolerance in primary care”] suggest that symptoms and self-reporting are not reliable diagnostic tools. Additionally, the data presented in various studies indicate variability and inconsistency in the diagnostic performance of symptoms and self-reported intolerance, further challenging their reliability. (Relevant)'

        Explanation: In this case, the chunks and hence summary support the idea of the statement where self reported and clinical diagnosis are unreliable in diagnosis of lactose intolerance. Hence it is Relevant with the correct classification.


        Input:

        Statement: {statement}
        List of Excerpts that supports the statement: {list_of_sieved_chunks}
        """.format(list_of_sieved_chunks=list_of_sieved_chunks,statement=statement)


        

        data={
            "model":"gpt-4o",
            "messages":[
                {"role": "user", "content": [{"type": "text","text": summarizer_prompt_support}]}
            ],
            "temperature":0
        }
        response = await async_client.chat.completions.create(**data)
    else:
        summarizer_prompt_oppose="""
        You are an expert summarizer and evaluator. Your role is to help determine whether a single paper is relevant in opposing the statement
        By ‘opposing,’ we mean that the extracts of the paper provides a viewpoint or information that contradicts or challenges the statement's main point.

        Instructions:

        Summarize the Key Idea of All Excerpts: Summarize the overall message conveyed by the excerpts in relation to the statement. Focus on how these excerpts challenge or contradict the statement’s validity.

        Use Original Text: In the summary, include the EXACT original text from the excerpts in square brackets [ ] for direct reference.

        Provide an Overall Assessment:

        Relevant: The paper is relevant in opposing the statement (contradicts or challenges the statement)
        Irrelevant: The paper is not relevant in opposing the statement (irrelevance to the statement)
        Support: The paper actually supports the statement instead, which in this case the sentiment of the extracts are identified wrongly
        Output Format:

        Summarize all excerpts concisely.
        End with the assessment score in brackets () (e.g., (Relevant), (Irrelevant), or (Support)). 
        Output the summary and the score in brackets () ONLY.

        Example of Support (to let you know what constitues as wrong classification)

        Input:
        Statement: 'A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhoea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance.'
        List of Excerpts that opposes the statement: 
        '['!The Author 2010.Published by Oxford University Press on behalf of the Association of Physicians.All rights reserved.For Permissions, please email: journals.permissions@oxfordjournals.orgQ J Med 2010; 103:555–572doi:10.1093/qjmed/hcq082Advance Access Publication 3 June 2010 by guest on October 13, 2011qjmed.oxfordjournals.orgDownloaded from Text on page 3:BackgroundLactose malabsorption is the most common type ofcarbohydrate malabsorption and is caused by lowlactase levels.1 Lactase activity is highest at birthand declines after weaning.The age at which thisdecline starts and the proportion of the adult popula-tion with lactase levels low enough to be consideredhaving ‘hypolactasia’ are both strongly related to eth-nicity, with highest rates of lactose malabsorption inAsian populations, Native Americans and AfricanAmericans (60–100%) and lowest rates in people ofnorthern European origin and the US white popula-tion (2–22%).2 When lactose malabsorption gives riseto symptoms, this is called ‘lactose intolerance’.Although lactose intolerance is often bothersome forpatients, once recognized it may be managed bysimple dietary adjustments.Diagnosing lactose intolerance is not straightfor-ward.', 'Rana SV, Mandal AK, Kochhar R, Katyal R, Singh K.Lactoseintolerance in different types of irritable bowel syndrome innorth Indians.Trop Gastroenterol 2001; 22:202–4.35.Sciarretta G, Giacobazzi G, Verri A, Zanirato P, Garuti G,Malaguti P.Hydrogen breath test quantification and clinicalcorrelation of lactose malabsorption in adult irritable bowelsyndrome and ulcerative colitis.Dig Dis Sci 1984; 29:1098–04.36.SzilagyiA,MalolepszyP,YesovitchS,NathwaniU,Vinokuroff C, Cohen A, et al.Inverse dose effect of pretestdietary lactose intake on breath hydrogen results and symp-toms in lactase nonpersistent subjects.Dig Dis Sci 2005;50:2178–82.37.Tolliver BA, Herrera JL, DiPalma JA.', 'When lactose malabsorption gives riseto symptoms, the result is called ‘lactose intoler-ance’.Although lactose intolerance is often bother-some for patients, once recognized it may bemanaged by simple dietary adjustments.However,diagnosing lactose intolerance is not straightfor-ward, especially in primary care.Aim:To summarize available evidence on the diag-nostic performance of gastrointestinal symptoms andself-reported milk (lactose) intolerance in primarycare, and the relationship between lactose malab-sorption and intolerance.Data sources:', 'GermanEnck, 199024316270.33 (0.08–0.70)0.96 (0.82-1.00)0.75 (0.19–0.99)0.18 (0.07–0.36)Ethnicity: caucasian no vs. yesTolliver, 1994371812291020.38 (0.25–0.54)0.90 (0.82–0.94)0.60 (0.41–0.77)0.22 (0.15–0.30)Gender: female vs. maleDiPalma, 1988221145947220.71 (0.63–0.78)0.27 (0.18–0.38)0.66 (0.58–0.73)0.68 (0.56–0.79)Gender: female vs. maleParker, 20013225608290.76 (0.58–0.89)0.33 (0.23–0.43)0.29 (0.20–0.40)0.22 (0.10–0.38)Gender: female vs. maleSzilagyi, 200536373622230.63 (0.49–0.75)0.39 (0.27–0.53)0.51 (0.39–0.63)0.49 (0.34–0.64)Gender: female vs. maleVernia, 1995391105247210.70 (0.62–0.77)0.29 (0.19–0.41)0.68 (0.60–0.75)0.69 (0.57–0.80)Milk intolerance awareness (yes vs. no)MI awarenessBianchi Porro, 19831932713250.71 (0.56–0.84)0.78 (0.60–0.91)0.82 (0.67–0.93)0.34 (0.20–0.51)Awareness of lactose-associated symptomsDiPalma, 1988224829113520.30 (0.23–0.38)0.64 (0.53–0.75)0.62 (0.51–0.73)0.69 (0.61–0.76)Awareness of food intoleranceEnck, 1988238611120.42 (0.20–0.67)0.67 (0.41–0.87)n.a.n.a.Self-reported MIFarup, 2004252301390.67 (0.09–0.99)0.57 (0.44–0.68)0.06 (0.01–0.21)0.03 (0.00–0.13)Self-reported MIGupta, 200726391743130.48 (0.36–0.59)0.43 (0.26–0.63)0.70 (0.56–0.81)0.77 (0.64–0.87)Self-reported MIMetz, 197530426130.40 (0.12–0.74)0.87 (0.60–0.98)0.67 (0.22–0.96)0.32 (0.13–0.57)Self-reported MIVernia, 2004815249138630.52 (0.47–0.58)0.56 (0.47–0.66)0.76 (0.69–0.81)0.69 (0.62–0.75)Daily milk intake <250 vs. >250 mlBozzani, 1986202421130.69 (0.51–0.83)0.60 (0.15–0.95)0.92 (0.75–0.99)0.79 (0.49–0.95)Milk consumption: no vs. yesSciarretta, 1984354042260.65 (0.51–0.76)0.60 (0.26–0.88)0.91 (0.78–0.98)0.79 (0.59–0.92)Milk consumption: no vs. yesBianchi Porro, 1983a,1932241380.71 (0.56–0.84)0.25 (0.12–0.43)0.57 (0.43–0.70)0.62 (0.38–0.82)Symptoms during and after LHBT (yes vs. no)Symptoms during LHBTBernardes-Silva, 2007172883360.90 (0.74–0.98)0.82 (0.67–0.92)0.78 (0.61–0.90)0.08 (0.02–0.21)Symptoms during LHBTBeyerlein, 200818338463382880.90 (0.86–0.93)0.38 (0.35–0.42)0.42 (0.39–0.46)0.12 (0.08–0.16)Symptoms during LHBTCasellas, 20082176662270.97 (0.91–0.99)0.29 (0.20–0.39)0.54 (0.45–0.62)0.07 (0.01–0.23)– Symptom score during LHBT 7Casellas, 2008a,21603018630.77 (0.66–0.86)0.68 (0.57–0.77)0.67 (0.56–0.76)0.22 (0.14–0.33)Symptoms during LHBTDiPalma, 1988221241331680.80 (0.73–0.860.84 (0.74–0.91)0.91 (0.84–0.95)0.31 (0.22–0.41)Symptoms during LHBT and 24 h thereafterFarup, 2004252261440.67 (0.09–0.99)0.63 (0.51–0.74)0.07 (0.01–0.24)0.02 (0.00–0.12)Symptoms during LHBTFernandez, 200641737190.50 (0.23–0.77)0.86 (0.65–0.97)0.70 (0.35–0.93)0.27 (0.12–0.48)Symptoms during LHBTGupta, 200726482041150.54 (0.43–0.65)0.43 (0.26–0.61)0.71 (0.58–0.81)0.73 (0.60–0.84)Symptoms during LHBTHermans, 199727671628720.89 (0.80–0.95)0.31 (0.25–0.37)0.29 (0.24–0.36)0.10 (0.04–0.19)(continued)Lactose malabsorption and intolerance567 by guest on October 13, 2011qjmed.oxfordjournals.orgDownloaded from Text on page 15:ingestion (sensitivity).', 'Vernia P, Di Camillo M, Marinaro V.Lactose malabsorption,irritable bowel syndrome and self-reported milk intolerance.Dig Liver Dis 2001; 33:234–9.41.Fernandez-Banares F, Rosinach M, Esteve M, Forne M,Espinos JC, Maria VJ.Sugar malabsorption in functionalabdominal bloating: a pilot study on the long-term effect ofdietary treatment.Clin Nutr 2006; 25:824–31.42.Lisker R, Solomons NW, Perez BR, Ramirez MM.Lactase andplacebo in the management of the irritable bowel syndrome:a double-blind, cross-over study.Am J Gastroenterol 1989;84:756–62.43.Bohmer CJ, Tuynman HA.The clinical relevance of lactosemalabsorptioninirritablebowelsyndrome.EurJGastroenterol Hepatol 1996; 8:1013–16.44.BohmerCJ,TuynmanHA.Theeffectofalactose-restricted diet in patients with a positive lactose tolerancetest,earlierdiagnosedasirritablebowelsyndrome:a 5-year follow-up study.Eur J Gastroenterol Hepatol 2001;13:941–4.45.']'

        Output: 
        'The excerpts collectively highlight the complexity and challenges in diagnosing lactose intolerance, particularly through clinical symptoms and self-reporting. They emphasize that while lactose intolerance can be managed through dietary adjustments, diagnosing it is not straightforward. For instance, [“Diagnosing lactose intolerance is not straightforward, especially in primary care”] and [“To summarize available evidence on the diagnostic performance of gastrointestinal symptoms and self-reported milk (lactose) intolerance in primary care”] suggest that symptoms and self-reporting are not reliable diagnostic tools. Additionally, the data presented in various studies indicate variability and inconsistency in the diagnostic performance of symptoms and self-reported intolerance, further challenging their reliability. (Support)'

        Explanation: In this case, the chunks and hence summary support the idea of the statement where self reported and clinical diagnosis are unreliable in diagnosis of lactose intolerance.

        Example of Relevant 

        Input:
        Statement: 'A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhoea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance.'
        List of Excerpts that opposes the statement: 
        '['Objective:To assess the clinical characteristics of Lactose intolerance (LI) as well as its relationship with demographic factors among diarrheal children below ïve years of age.Methods:A cross sectional study was conducted enrolling 50 diarrheal patients in equal proportion by gender.The present study was conducted over children suffering from profuse diarrhea admitted to the Pediatrics ward at LUMHS and CIVIL hospital Hyderabad, Pakistan during July 2018 to January 2019.The questionnaire-based analysis was conducted to gather information regarding dietary index and manifestation of symptoms after milk consumption.Clinical analysis was performed using lactose tolerance test, Stool pH and reducing substance respectively.The obtained results were analyzed using SPSS.Results: 20 children were found to be suffering from lactose intolerance.', 'The clinical symptoms observed among individuals affected by LI included loose motion, weight loss, abdominal distention, and the presence of pus cells in stool indicating the signs of infection.T-test showed statistical signiïcance (p-value < 0.05) over physical attributes such as height and number of pus cells among LI patients as compared to lactose tolerant (LT) patients.The ïnding of pus cells in the stool simultaneous to the strong statistical correlation between relieve in symptoms with increasing age also aírmed the existence of secondary type hypo-lactasia.The study also highlighted the demographic aspects contributing to the prevalence of the condition.Conclusions:Secondary lactose intolerance was found with shortened heights of patients and increased number of pus cells in stool.VOL. 05, ISSUE. 06 JUNE 2022Keywords:Lactose Intolerance, Diarrhea, Gut Health, Lactose Tolerance Test, Lactase*Corresponding Author:', 'Clinical Assessment and Demographic Insights of Lactose Intolerance Among Diarrheal Children at Hyderabad, Pakistan:Lactose Intolerance Among Diarrheal Children .Pakistan BioMedical Journal, 7(02). https://doi.org/10.54393/ pbmj.v7i02.1030Yousuf M et al.,  DOI: https://doi.org/10.54393/pbmj.v7i02.1030Lactose Intolerance Among Diarrheal ChildrenText on page 2:(commonly known as adult lactose intolerance) is characterized as a condition where the patients present normal lactose expression after birth, which gradually declines during growing up.On the other hand, secondary lactose intolerance may develop in a person with a healthy small intestine during episodes of acute illness causing mucosal damage or from medications resulting from certain gastrointestinal disease.This type of lactose intolerance can occur in both infants and adults and is generally reversible [5].A number of methods have been reported to assess the degree of lactose intolerance such as the hydrogen breath test, the milk tolerance test, and diet elimination protocol reducing sugar and stool pH detection test [6-8].', 'The value of n was calculated as 48.98 or ~ 49.Children suffering from any organic disease (chicken pox, measles etc.) were excluded from the study.We also excluded children already taking lactose free diet from our study so as to avoid bias in results of the study.The study was designed based on the data obtained in the form of a questionnaire along with the clinical samples collected over the period of time.The study was conducted with the ethical approval of the ethical committee on 15-10-2018 at the Institute of Biochemistry, University of Sindh (Jamshoro) with a reference number IOB/125/2018.The patients were categorized into two groups Lactose tolerant (LT) and Lactose Intolerant (LI).In both groups the patients suffered from mild to severe diarrhea, however, the patients classiïed in LI group showed recurrence of symptoms after diet elimination protocol and lactose tolerance test.On the contrary, the patients in the LT group showed no such outcome.For lactose tolerance test, patients were allowed to ingest 500 mL approx. of lactose-containing milk followed by the measurement of their blood glucose levels prior to and later to the ingestion [9].', 'PBMJ, Published by Crosslinks International PublishersPBMJ VOL. 7 Issue. 2 February 2024Yousuf M et al.,  DOI: https://doi.org/10.54393/pbmj.v7i02.1030Lactose Intolerance Among Diarrheal ChildrenText on page 3:Table 1:Comparative analysis of blood glucose levels prior (baseline) and after the ingestion of lactose at different time intervals between LI and LT group. test and the p-values obtained among LI and LT patients after 30 and 60 minutes.The glycemic index (glucose levels) showed signiïcant correlation between two groups LI and LT after the intake of milk in comparison to baseline.This showed that glycemic index can be accounted as a reliable parameter in the assessment of lactose intolerance.Mean ± SDMean ± SDLT (Lactose atdifferent time intervals)Baseline96.5 ± 16.3139.8 ± 26.2134.8 ± 35.492.9 ± 12.40.330.0000170.00005105.8 ± 15.84101.4 ± 12.24Variablesp –valueLI(Lactose intolerant)Mean ± SD30 minutes60 minutesPresence of reducing sugar in stool was tested to categorize patients in two groups i-e lactose tolerant and lactose intolerant.', 'Based on the test results, out of 50 patients, 17 patients were diagnosed as lactose intolerant.However, 03 patients showed negative results despite of the persistent symptoms of LI (Figure 1).Figure 1:Prevalence of lactose intolerance on basis of fecal reducing substance.Upon measurement of the stool pH of ïfty patients, we found that the ones conïrmed as lactose intolerant had a slightly acidic pH (5.5 - 5.9) compared to the lactose tolerant (7.0 – 7.5) patients.Moreover, in our assessment, the most prevalent symptoms observed in the LI case included Loose motion (L/M) with mucus, weight loss, vomiting and abdominal distention.The statistical analysis indicated a signiïcant relationship between the LI condition and the height (L) and the number of pus cells (pc) found in the stool of the affected LI patients in comparison to lactose tolerant patients (Figures 2a-c).The obtained p-values were 0.03, 0.08, and 0.01 for height, body mass and the number of pus cells, respectively.Figure 2:Statistical signiïcance of physiological parameters2a:', 'Length, 2b:Mass and 2c:Presence of pus cells among LI and LT patients, respectively. p-value < 0.05 was considered as signiïcant.42Copyright © 2024.PBMJ, Published by Crosslinks International PublishersPBMJ VOL. 7 Issue. 2 February 2024Fecal reducing testLactose tolerantLactose IntolerantAnomalies30173Boxplot of LI length, LT length 1009080706050DataLILLTL(a)98765432Boxplot of LI Mass, LT MassDataLI MassLT Mass(b)20151050DataBoxplot of PC LI, PC LTpc LIpc LT(c)Yousuf M et al.,  DOI: https://doi.org/10.54393/pbmj.v7i02.1030Lactose Intolerance Among Diarrheal ChildrenText on page 4:C O N C L U S I O N SThe current study aimed to understand the clinical and demographic attributes among patients suffering from hypo-lactasia.The common symptoms included vomiting, abdominal distension, loose motion, and weight loss accompanied by the release of mucus in the stool of LI patients.The children suffering from such intolerance had shortened height and may present an increased number of pus cells in stool.', 'Catanzaro R, Sciuto M, Marotta F.Lactose intolerance:An update on its pathogenesis, diagnosis, and treatment.Nutrition Research. 2021 May; 89: 23-34. doi: 10.1016/j.nutres.2021.02.003.Robles L and Priefer R.Lactose intolerance:What your breath can tell you.Diagnostics. 2020 Jun; 10(6): 412. doi: 10.3390/diagnostics10060412.Heyman MB.Committee on Nutrition.Lactose intolerance in infants, children, and adolescents.Pediatrics. 2006 Sep; 118(3): 1279-86. doi: 10.1542/ peds.2006-1721.Beyerlein L, Pohl D, Delco F, Stutz B, Fried M, Tutuian R.Correlation between symptoms developed after the oral ingestion of 50 g lactose and results of hydrogen breath testing for lactose intolerance.Alimentary Pharmacology and Therapeutics. 2008 Apr; 27(8): 659-65. doi: 10.1111/j.1365-2036.2008. 03623.x.']'
        Output: 
        'The excerpts collectively highlight the clinical symptoms and diagnostic methods for lactose intolerance, emphasizing the reliability of clinical symptoms and self-reporting in diagnosing the condition. Key points include:

        1. Clinical symptoms such as "loose motion, weight loss, abdominal distention, and the presence of pus cells in stool" are significant indicators of lactose intolerance [The clinical symptoms observed among individuals affected by LI included loose motion, weight loss, abdominal distention, and the presence of pus cells in stool indicating the signs of infection].
        2. The study used various diagnostic methods, including the lactose tolerance test, stool pH, and reducing substance tests, to confirm lactose intolerance [Clinical analysis was performed using lactose tolerance test, Stool pH and reducing substance respectively].
        3. The presence of symptoms like "vomiting, abdominal distension, loose motion, and weight loss" was consistently observed in lactose intolerant patients [The common symptoms included vomiting, abdominal distension, loose motion, and weight loss accompanied by the release of mucus in the stool of LI patients].
        4. The study found a significant correlation between clinical symptoms and lactose intolerance, suggesting that these symptoms are reliable indicators [The statistical analysis indicated a significant relationship between the LI condition and the height (L) and the number of pus cells (pc) found in the stool of the affected LI patients in comparison to lactose tolerant patients].
        (Relevant)'
        Explanation: In this case, the chunks and hence summary oppose the idea of the statement where self reported and clinical diagnosis are unreliable in diagnosis of lactose intolerance and in fact it says they are reliable, which is what the statement is NOT taking about. Hence it opposes the statement and is hence relevant with the correct classification.

        Input:

        Statement: {statement}
        List of Excerpts that opposes the statement: {list_of_sieved_chunks}
        """.format(list_of_sieved_chunks=list_of_sieved_chunks,statement=statement)
        
        data={
            "model":"gpt-4o",
            "messages":[
                {"role": "user", "content": [{"type": "text","text": summarizer_prompt_oppose}]}
            ],
            "temperature":0
        }
        response = await async_client.chat.completions.create(**data)


    return response.choices[0].message.content


async def extract_to_edit(file_content):
    extraction_prompt = f"""
    You are an advanced citation and reference extraction assistant.

    Your task is to:
    1. Extract statements from the provided document that include in-text citations. 
    2. Match the citations in those statements to the corresponding entries in the reference list at the end of the document.
    3. Return the output as a structured list where:
       - Each element contains:
         [Statement, [[citation, Name of Reference article in reference list], ...]]
    Note: Statement means The statement ONLY without the citation!
    
    Here is the content of the document:
    ----
    {file_content}
    ----

    Only output the structured list in the specified format. Do not include explanations or any additional information.
    """
    system_prompt = "You are a structured data extraction agent. Extract the requested information and output it as a structured list only."
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": extraction_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content

async def extract_statement_citation(text, new_statements):
    print(new_statements)
    extraction_prompt = f"""
    You are a text editor. You edit the following text:
    {text}
    Your input: [Statement(citation),...]

    Your task:
    1. Locate the statement in the text
    2. Replace the statement and it's citation in the text with the statement and it's citation in the list
    3. Output the text with the inserted edits

    Input: {new_statements}
    Output:
    """

    system_prompt = "You are a text editor. You edit the text based on a list of statements."
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": extraction_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content


async def convert_to_replace(row,text):
    replace_prompt = f"""
    You are an advanced citation generator tasked with creating structured citations and references. Use the following document as your reference source:

    ----
    {text}
    ----
    The row is formatted as follows:
    [Statement with Author and year pair, Reference article names in a list]

    Based on the data provided in the row, generate citations and references in the same format as those in the document. If the row already contains the exact same citations and references as the document, simply repeat the same output. Otherwise, use the row's information to create new citations and references.
    For example: 
    In document;
    Statement with citation: ' A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhoea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance (Jellema et al., 2010).'
    Reference: 'Jellema P. et al. (2010). Lactose malabsorption and intolerance: a systematic review on the diagnostic value of gastrointestinal symptoms and self-reported milk intolerance. Q J Med; 103:555-572.'


    Your input from the row:
    ['A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhoea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance. (Salah M Bakry, Ziad Banoun, Ammar Abdulfattah, Fawaz M Alkhatib, Mussad Almhmadi, Mohammed Alharbi, Adel A Alluhaybi, M. O. Krenshi, Fahad Alharthi, S. Ekram (2023); Julia Leszkowicz, K. Plata-Nazar, A. Szlagatys-Sidorkiewicz (2022); Muhammad Yousuf, Beenish Khanzada, Mehvish Jabeen Channa, Autif Hussain Mangi, Fahim Ullah Khan (2024); Julia Leszkowicz, K. Plata-Nazar, A. Szlagatys-Sidorkiewicz (2022); Julia Leszkowicz, K. Plata-Nazar, A. Szlagatys-Sidorkiewicz (2022); Muhammad Yousuf, Beenish Khanzada, Mehvish Jabeen Channa, Autif Hussain Mangi, Fahim Ullah Khan (2024))',['Comparison of Knowledge of Lactose Intolerance and Cow’s Milk Allergy Among the Medical Students at Two Universities in Saudi Arabia', 'Can Lactose Intolerance Be a Cause of Constipation? A Narrative Review', 'Clinical Assessment and Demographic Insights of Lactose Intolerance Among Diarrheal Children at Hyderabad, Pakistan', 'Can Lactose Intolerance Be a Cause of Constipation? A Narrative Review', 'Can Lactose Intolerance Be a Cause of Constipation? A Narrative Review', 'Clinical Assessment and Demographic Insights of Lactose Intolerance Among Diarrheal Children at Hyderabad, Pakistan']]
    Your output:

    ['A meta-analysis reveals that clinical symptoms (abdominal pain, diarrhea) or self-reporting are not reliable indices for the diagnosis of lactose intolerance (Bakry et al., 2023; Leszkowicz et al., 2022; Yousuf et al., 2024).',['(Salah M Bakry et al., 2023). Comparison of Knowledge of Lactose Intolerance and Cow’s Milk Allergy Among the Medical Students at Two Universities in Saudi Arabia']].

    Take note that you replace the original references and citations with whatever is in the row. WHatever is in the row can include old and new references or just new references. Just follow suit.
    Row data:
    {row}

    **Output format**:
    ['Statement(citation)',['Reference 1',...]]
    Take note that even if single reference, still need quotation around it in a list

    Ensure the output strictly follows the format above, with accurate citations and references aligned to the style in the document.

    """
    system_prompt = """You are an advanced citation and reference generator. Your task is to generate structured citations and references based on the provided input. 

                    - Ensure all citations and references strictly align with the requested format and style.
                    - Ensure statements match exactly for regex-based comparisons.
                    - If matching references are found, output them in the exact same format as they appear in the document to enable regex matching.
                    - Use only the information from the provided document and row data to create the output.
                    - If the input data matches the existing references in the document, repeat them exactly.
                    - Respond with the output **only** in the specified structured format: [Statement(citation), Reference].
                    """
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": replace_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content



async def find_to_edit_statement(text,statement_list):
    extraction_prompt = f"""
    You are a citation editor. With reference to the list of statements with citation, edit the text by 
    1) Removing citations from the text that are missing in the list of statements with citation. 
    AND/OR
    2) Adding citations in the list of statements of citations not in text. 
    Output the edited text only with the exact same format as the original text. YOU CAN DO 1 AND 2 SIMULTANEOUSLY IF NEEDED.

    ----
    The text is:
    {text}
    The list of statements with citation is:
    {statement_list}
    ----

    """
    system_prompt = "You are a statement and citation locator and editor. Locate the statements and edit the statements and citations in the text based on the list of statements and output the edited text. ONLY OUTPUT THE EDITED TEXT."
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": extraction_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content


async def find_reference_list(text):
    extraction_prompt = f"""
    You are a reference list locator. You locate the reference list and output the heading of the reference list as well as all references as it is. Make sure it is the exact wording.
    ----
    The text is:
    {text}
    ----

    """
    system_prompt = "You are a reference list locator. Output the located reference list exactly as it is in the text."
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": extraction_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content


async def replace_reference_list(reference_list,remove_list,add_list):
    print(remove_list)
    print(add_list)
    replacement_list_prompt = f"""
    You are a reference list editor. Edit the Reference list by:
    1. Removing references found in the Reference removal list.
    2. Adding references found in the Reference addition list.

    ### Instructions:
    - Make sure edits to the reference list follows the referencing style in the reference list
    - Remove duplicates in the final list
    - Ignore references in the removal list that do not exist in the Reference list.
    - Ignore references in the addition list that already exists in the Reference list.
    - Add new references at the end of the Reference list if they are not already present.

    ### Example:

    #### Input:
    Reference list:
    - Smith, J. (2020). Title of Reference 1.
    - Doe, J. (2019). Title of Reference 2.
    - Brown, A. (2018). Title of Reference 3.

    Reference removal list:
    - Doe, J. (2019). Title of Reference 2.

    References addition list:
    - White, B. (2021). Title of Reference 4.
    - Brown, A. (2018). Title of Reference 3.

    #### Output:
    Reference list:
    - Smith, J. (2020). Title of Reference 1.
    - Brown, A. (2018). Title of Reference 3.
    - White, B. (2021). Title of Reference 4.

    ---

    ### Input:
    Reference list:
    {reference_list}

    Reference removal list:
    {remove_list}

    References addition list:
    {add_list}

    ---

    ### Output:
    Reference list:

    """

    system_prompt = "You are a reference list creator. You edit the reference list according to the remove reference list and add reference list and output ONLY the edited reference list."
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": replacement_list_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    print(response.choices[0].message.content)
    return response.choices[0].message.content

async def citation_extractor(whole_statement):
    finder_prompt = f"""
    You are a citation extractor. You extract citations (including parenthesis) from the sentences and output the citations.
    Sentences:
    {whole_statement}

    """
    system_prompt = "You are a citation extractor. You extract citations together with their brackets. You return the citations ONLY"
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": finder_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content


async def edit_citationer(row,text):
    replace_prompt = f"""
    You are an advanced citation generator tasked with creating structured citations and references. Use the following document only as a style reference for formatting citations and references:
    ----
    {text}
    ----
    The row is formatted as:

    Edits: A text.
    References: A list of article names to be cited for the edits.

    Rules:
    1. Do Not Use Content from the Document:

        The document serves only as a style guide for formatting citations and references.
        Do not extract or infer content (statements or references) from the document unless explicitly specified.
    2. Use the Row Data Exclusively:

        Generate the updated statement and references using only the data provided in the row (Edits and References).
    3. Check for Proper Formatting:

        Ensure citations in the Edits follow the citation style in the document (e.g., "Author et al., Year").
        Ensure references in the References are formatted to match the style in the document.
    Output Requirements:

    Create the Edits with formatted citations. USE THE CONTENT IN THE EDIT ONLY FOR THE EDIT AND THE REFERENCE FOR THE CITATION
    Return the updated statement and reference list in the following format:
    Sample output:
    ['Edits (citations)', ['Reference 1', 'Reference 2']]

    Even if there is only one reference, it must be enclosed in a list.
    Ensure all citations and references strictly follow the format and style of the document   

    Input:
    {row}

    """
    system_prompt = """You are an advanced citation and reference generator. Your task is to generate structured citations and references based on the provided input. 

                    - Ensure all citations and references strictly align with the requested format and style.
                    - Use only the information from and row data to create the output and structure from the document to structure the output
                    - Respond with the output **only** in the specified structured format: [Statement(citation), [Reference]].
                    """
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": replace_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content


async def add_edits(list,text):
    add_prompt = f"""
    You are a text editor. You edit the following text:
    {text}
    Your input: [[Statement to place edit behind (put behind it's citation as well),edit (with citation), reference],...]

    Your task:
    1. Locate the statement in the text
    2. Insert the edit with it's citation behind the statement and the statement's citation
    3. Output the text with the inserted edits

    Input: {list}
    Output:
    """
    system_prompt = "You are a text editor. You edit the text and output the edited text."
    data={
        "model":"gpt-4o",
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text","text": add_prompt}]}
        ],
        "temperature":0
    }
    response = await async_client.chat.completions.create(**data)
    return response.choices[0].message.content


    