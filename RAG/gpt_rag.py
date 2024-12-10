import os
import subprocess
import requests
from dotenv import load_dotenv
from openai import AzureOpenAI
from bs4 import BeautifulSoup
import time
import pandas as pd
import unicodedata
import json
import logging


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

# Function to refresh the token if it has expired
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

            # Set the new token in environment variables and reinitialize the client
            os.environ['AZURE_OPENAI_API_KEY'] = access_token
            logging.info("Access token refreshed successfully.")
        else:
            logging.error("Failed to refresh access token.")
            exit(1)  # Exit if unable to refresh the token

# Function to initialize the AzureOpenAI client
client = None
def initialize_client():
    global client
    try:
        refresh_token_if_needed()  # Ensure token is valid before initializing
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=access_token,  # Use the refreshed token here
            api_version=api_version
        )
        logging.info("Azure OpenAI client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Azure OpenAI client: {e}")
        exit(1)

# Initialize the client
initialize_client()

# Function to retry operations with token refresh on Unauthorized error
def retry_on_exception(func, *args, max_retries=3, retry_delay=2, **kwargs):
    attempt = 0  # Initialize the attempt counter
    current_delay = retry_delay  # Use a separate variable to keep track of the current delay

    while attempt < max_retries:
        try:
            logging.info(f"Attempting {func.__name__} (Attempt {attempt + 1}/{max_retries}) with delay {current_delay}s...")
            
            # Refresh token if needed before each attempt
            refresh_token_if_needed()
            
            # Try executing the function
            return func(*args, **kwargs)

        except Exception as e:
            error_message = str(e)  # Capture the error message
            logging.error(f"Error encountered: {error_message}")

            # Check for specific errors that might need token refresh or longer delays
            if "401" in error_message or "Unauthorized" in error_message:
                logging.warning("Unauthorized error detected. Refreshing access token and retrying...")
                refresh_token_if_needed()
            elif "429" in error_message or "Too Many Requests" in error_message:
                logging.warning("Rate limit error detected. Consider increasing delay or reducing request frequency.")
                
            # Increment the attempt count
            attempt += 1

            # Log the retry information
            logging.error(f"Attempt {attempt} failed with error: {e}. Retrying in {current_delay} seconds...")

            # Wait for the current delay duration before retrying
            time.sleep(current_delay)

            # Increase the delay for the next attempt (exponential backoff)
            current_delay *= 2

    # If all retries fail, log the final failure
    logging.error(f"All {max_retries} attempts failed for {func.__name__}. Returning None.")
    return None



# Get names of all PDF articles
def naming(text):
    def func():
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": "What is the name of the article? Return the name only."},
                {"role": "user", "content": [{"type": "text", "text": text}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)

def read_text_file(file_path):
    """
    Reads the contents of a text file and returns as a string.
    
    Args:
    - file_path (str): Path to the text file.
    
    Returns:
    - str: Contents of the text file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content


#Replaces the numeric naming of files to the actual names of files using gpt 4o
def get_names(processed_texts,directory):
    def split_text_if_necessary(text, token_limit):
        tokens = text.split()
        if len(tokens) > token_limit:
            half_index = len(tokens) // 2
            return ' '.join(tokens[:half_index])
        return text
    for i in range(len(processed_texts)):
        input_path = os.path.join(directory, processed_texts[i])
        with open(input_path, 'r', encoding='utf-8') as f:
            processed_text = f.read()
            cleaned_text = ''.join(char for char in processed_text if unicodedata.category(char)[0] != 'C')
            cleaned_text = split_text_if_necessary(cleaned_text, token_limit=2000)
            name = naming(cleaned_text)
            processed_texts[i] = str(name)
    
    return processed_texts




system_prompt="In the following text, what are the full texts of each reference (can be multiple sentences), the name of the reference articles, the year the articles were published and the author(s) of the articles? Format your response in this manner:[['The lactase activity is usually fully or partially restored during recovery of the intestinal mucosa.','Lactose intolerance in infants, children, and adolescents','2006','Heyman M.B' ],...]"


# Get the references and the cited articles' names in the main article
def get_references(text):
    def func():
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [{"type": "text", "text": text}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)


# Get the text that the reference inb the main article is citing in the reference article
def similiar_ref(text, ref):
    def func():
        # query = "You are a reference fact checker. You check if the reference can be found in the abstract of the article in terms of semantic meaning. If yes, you highlight the information in the abstract of the article exactly as it is (Don't summarise or change anything). Output the semantically similar information only."
        query='Extract the sentence or sentences in the abstract that is most semantically similiar to the reference.'
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": query},
                {"role": "user", "content": [{"type": "text", "text": f"Reference: {text}, Abstract:{ref}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)


#Clean up gpt 4o output in getting the text that the references in main articles are citing as the format can be off. 
def clean_responses(sentence):
    def func():
        query = "Tidy up the following text to output sentence(s). Don't include unnecessary jargons like Text Content and PDF..."
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": query},
                {"role": "user", "content": [{"type": "text", "text": f"The text is: {sentence}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)


# def rearrange_list(text, list):
#     def func():
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": 'You are a semantic ranker. You rank the list according to how semantically similar the text in the list is to the text for comparison. Make sure that if the text for comparison is positive about a certain subject, the text in the list is ALSO positive about that SAME subject and VICE VERSA. You output the rank of the list as a list of indexes ONLY.'},
#                 {"role": "user", "content": [{"type": "text", "text": f"Text for comparison: {text}. List: {list}"}]}
#             ]
#         )
#         return response.choices[0].message.content

#     return retry_on_exception(func)

# def check_gpt(output):
#     def func():
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": 'You check if the input is in the form of a list like e.g. [0,1,2,3,4,5]. If it is, output the input as it is ONLY...'},
#                 {"role": "user", "content": [{"type": "text", "text": f"Input: {output}"}]}
#             ]
#         )
#         return response.choices[0].message.content

#     return retry_on_exception(func)



def rank_and_check(text, list):
    def func():
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": 'You are a semantic ranker. You rank the list according to how semantically similar the text in the list is to the text for comparison. You output the rank of the list as a list of indexes ONLY like [0,2,3,4,5,1]. Make sure your max index is length of list - 1.'},
                {"role": "user", "content": [{"type": "text", "text": f"Text for comparison: {text}. List: {list}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)

# def clean_away_nonsemantic(text):
#     def func():
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": 'When the text says anything related to no semantic meaning or similarity or anything related to information not begin found, output *. Else, output the text as it is.'},
#                 {"role": "user", "content": [{"type": "text", "text": f"Text:{text}"}]}
#             ]
#         )
#         return response.choices[0].message.content

#     return retry_on_exception(func)


# def keyword_search(text):
#     #original
#     kws1="What are the keywords in the Text? Take note these keywords will be used for a graph search in semantic scholar. Output the keywords ONLY."
#     #Making keywords a focus on main topic - idea is to narrow down focus - more accurate papers returned
#     kws2= f"""
#     What are the main topics in the Text? Take note that these topics will be used as keywords for keyword searching. Output the topics as keywords and ONLY output the keywords with them being separated by commas if there are more than one keyword.
#     """
#     kws3="""What are the main topics in the text? The topics should be used as keywords for keyword searching. Output the topics as keywords and only output the keywords as a list. If certain topics are closely related, group them together as a single string inside the main list.

#     Rules:

#     1. Group closely related topics (e.g., "prebiotics" and "probiotics") into a single string like 'prebiotics, probiotics'.
#     2. If a topic stands on its own (e.g., "lactose tolerance"), list it separately.
#     3. Always format the output as a single list of strings.
#     Example: Text: "A proportion of the world’s population is able to tolerate lactose as they have a genetic variation that ensures they continue to produce sufficient quantities of the enzyme lactase after childhood."
#     Output: ['lactose tolerance', 'genetic variation, enzyme lactase', 'lactose tolerance, childhood']
#     """
#     kws4="""
#     What are the keywords in terms of topics for the Text? Use the keywords to write keyword searches based on the keywords identified from the Text. Combine keywords if you think they relate to each other. 
#     Output the keyword searches as a list of strings ONLY in the format: ['lactase activity restoration', 'lactase activity recovery', ...]
#     """
#     def func():
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": kws3},
#                 {"role": "user", "content": [{"type": "text", "text": f"Text:{text}" }]}
#                 #{"role": "user", "content": [{"type": "text", "text": kws2}]}
#             ]
#         )
#         return response.choices[0].message.content

#     return retry_on_exception(func)


#Provide a summary for each subdocument to allow for quicker search
def summarise_subdocument(text):
    def func():
        query='Provide a summary of the text.'
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": query},
                {"role": "user", "content": [{"type": "text", "text": f"Text:{text}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)

#locate subdocument where ref is most likely found in
def locate_subdoc(summary, ref):
    def func():
        # query = "You are a reference fact checker. You check if the reference can be found in the abstract of the article in terms of semantic meaning. If yes, you highlight the information in the abstract of the article exactly as it is (Don't summarise or change anything). Output the semantically similar information only."
        query='You are a relation checker. Output yes if the Summary and Reference is related. Output no otherwise'
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": query},
                {"role": "user", "content": [{"type": "text", "text": f"Summary: {summary}, Reference: {ref}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)




#retrieve chunks of the document that are semantically similar to text
# def retriever(chunk, ref):
#     def func():
#         #query="Compare the Reference Article Text to the Text Referencing The Reference Article. Analyze whether the Reference Article Text or ANY part of it (whether it is one sentence or more) supports the Text Referencing The Reference Article. By 'support', we mean text in Reference Article Text that substantiate the Text Referencing The Reference Article, whether it is semantically similar or semantically opposite. If it does, respond with ‘yes’; otherwise, respond with ‘no’. "
#         query = """
#         Compare the Reference Article Text to the Text Referencing The Reference Article. Analyze whether the Reference Article Text or ANY part of it (whether it is one sentence or more) supports the Text Referencing The Reference Article.

#         By 'support,' we mean text in the Reference Article Text that substantiates, elaborates on, or is relevant to the claims made in the Text Referencing The Reference Article, whether it is semantically similar. Support does not require exact word matching but rather conceptual or factual alignment.

#         Guidelines:
#         - "Semantically similar" means the Reference Article Text provides information that agrees with or reinforces the Referencing Text.
#         - Partial matches are acceptable, and the support can span multiple sentences if necessary.
#         - You do not need to extract specific sentences, only determine whether support exists.

#         If the Reference Article Text supports the Text Referencing The Reference Article in any way, respond with ‘yes’ Otherwise, respond with ‘no’

#         Example:
#         Reference Article Text: "Lactose malabsorption often results in gas production."
#         Text Referencing The Reference Article: "Individuals who can digest lactose do not face any gastric issues."

#         Response: 'yes' (The Reference Article talks about gas production, while the Referencing Text talks about how those who can digest lactose do not face any gastric issues, but both discuss gas production (gastric issues relates to flatulence and bloating which is gas production) in relation to lactose digestion, hence they are still relevant.)
#         """
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": query},
#                 {"role": "user", "content": [{"type": "text", "text": f"Reference Article Text: {chunk}, Text Referencing The Reference Article: {ref}"}]}
#             ]
#         )
#         return response.choices[0].message.content

#     return retry_on_exception(func)

# def siever(chunk, ref):
#     def func():
#         #query="Sieve out the texts in the 'Text' that support the 'Reference'. By support, we mean text in 'Text' that substantiate the 'Reference', whether it is semantically similar or semantically opposite. If the text matches partially or fully, extract it. For example: Your Input: Text: Bacterial fermenta-tion of lactose results in production of gasses including hydrogen (H2), carbon dioxide (CO2), methane (CH4) and short chain fatty acids (SCFA) that have effects on GI function (figure 1).Lactose intoleranceLactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI).However, the two must not be confused and the causes of symptoms must be considered separately.Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1) whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy) and bloating after lactose intake (figure 1)., Reference: The bacteria in the large intestine ferment the lactose, resulting in gas formation which can cause symptoms such as bloating and flatulence after lactose ingestion. Your Output: Bacterial fermenta-tion of lactose results in production of gasses including hydrogen (H2), carbon dioxide (CO2), methane (CH4) and short chain fatty acids (SCFA) that have effects on GI function (figure 1).Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1) whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy) and bloating after lactose intake (figure 1).If there are no supporting texts, output 'no'."
#         # query="Sieve out the texts in the Text that supports the Reference. For example: Your Input: Text: Bacterial fermenta-tion of lactose results in production of gasses including hydrogen (H2), carbon dioxide (CO2), methane (CH4) and short chain fatty acids (SCFA) that have effects on GI function (figure 1).Lactose intoleranceLactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI).However, the two must not be confused and the causes of symptoms must be considered separately.Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1) whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy) and bloating after lactose intake (figure 1)., Reference: The bacteria in the large intestine ferment the lactose, resulting in gas formation which can cause symptoms such as bloating and flatulence after lactose ingestion. Your Output: Bacterial fermenta-tion of lactose results in production of gasses including hydrogen (H2), carbon dioxide (CO2), methane (CH4) and short chain fatty acids (SCFA) that have effects on GI function (figure 1).Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1) whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy) and bloating after lactose intake (figure 1)."
#         query="""
#         Extract the parts of the 'Text' that support the 'Reference'. By 'support,' we mean any portion of the 'Text' that substantiates or aligns with the 'Reference' through semantic similarity (i.e., conveying the same or closely related meaning).

#         Guidelines:
#         1. 'Support' includes direct or paraphrased information that aligns with or opposes the 'Reference' in a meaningful way.
#         2. Both partial and full matches are acceptable, and multiple sentences can be considered as part of the extraction if needed.
#         3. If no supporting text exists, output 'no.'

#         Example:

#         Input:
#         Text: Bacterial fermenta-tion of lactose results in production of gasses including hydrogen (H2), carbon dioxide (CO2), methane (CH4) and short chain fatty acids (SCFA) that have effects on GI function (figure 1).Lactose intoleranceLactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI).However, the two must not be confused and the causes of symptoms must be considered separately.Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1) whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy) and bloating after lactose intake (figure 1).

#         Reference: The bacteria in the large intestine ferment lactose, resulting in gas formation which can cause symptoms such as bloating and flatulence after lactose ingestion.

#         Expected Output: 
#         Bacterial fermenta-tion of lactose results in production of gasses including hydrogen (H2), carbon dioxide (CO2), methane (CH4) and short chain fatty acids (SCFA) that have effects on GI function (figure 1).Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1) whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy) and bloating after lactose intake (figure 1).

#         If no supporting texts are found, respond with 'no'
#         """
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": query},
#                 {"role": "user", "content": [{"type": "text", "text": f"Text: {chunk}, Reference: {ref}"}]}
#             ]
#         )
#         return response.choices[0].message.content

#     return retry_on_exception(func)


# def retriever_and_siever(chunk, ref):
#     def func():
#         pro = """
#         Compare the 'Reference Article Text' (which is a chunk of the reference article) to the 'Text Referencing The Reference Article' (which cites the reference article). Identify which parts of the 'Reference Article Text' are being cited or referenced by the 'Text Referencing The Reference Article.'

#         By 'citing,' we mean that the 'Text Referencing The Reference Article' refers to or aligns with the information, facts, or concepts in the 'Reference Article Text.' The match can be direct, paraphrased, or conceptually similar.

#         Guidelines:
#         - Extract ALL relevant parts of the 'Reference Article Text' (chunk) that is being referenced in the 'Text Referencing The Reference Article.' You may output the whole 'Reference Article Text' (chunk) if the whole chunk is relevant.
#         - The match does not need to be exact; it can be a paraphrased or conceptually aligned statement.
#         - Consider not only direct references, but also cases where the 'Text Referencing The Reference Article' discusses related facts or concepts in different wording.
#         - If no part of the 'Reference Article Text' is cited, respond with 'no'.

#         Important Note:
#         There might be cases where the phrasing between the 'Reference Article Text' and the 'Text Referencing The Reference Article' differs, but the underlying concepts are aligned. For example, if the 'Reference Article Text' discusses gas production due to bacterial fermentation of lactose and the 'Text Referencing The Reference Article' discusses bloating and flatulence after lactose ingestion, these are conceptually aligned, and the relevant portion from the 'Reference Article Text' should be extracted.

#         Example of Matching Case:

#         Input:
#         'Reference Article Text: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Lactose intolerance. Lactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI). However, the two must not be confused and the causes of symptoms must be considered separately. Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).

#         Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

#         Output:
#         'Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).'

#         Example of Non-Matching Case (When to Respond with 'No'):

#         Input:
#         'Reference Article Text: Lactase persistence is common among populations of Northern European descent. The LCT −13’910:C/C genotype is associated with the ability to digest lactose in adulthood.

#         Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

#         Output:
#         'no'

#         Why this case results in 'no':
#         In this case, the 'Reference Article Text' discusses lactase persistence and a genetic factor related to lactose digestion, while the 'Text Referencing The Reference Article' discusses gas formation due to bacterial fermentation of lactose. These are different concepts, and no alignment exists between the two texts. Therefore, the correct response is 'no.'
        
#         Output ONLY the extraction. (the quoted texts after Output: in examples shown)
#         """
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": pro},
#                 {"role": "user", "content": [{"type": "text", "text": f"Reference Article Text: {chunk}, Text Referencing The Reference Article: {ref}"}]}
#             ]
#         )
#         return response.choices[0].message.content

#     return retry_on_exception(func)





"""Prompts:"""
# prot = f"""
#         Compare the 'Reference Article Text' (which is a chunk of the reference article) to the 'Text Referencing The Reference Article' (which cites the reference article). Identify which parts of the 'Reference Article Text' are being cited or referenced by the 'Text Referencing The Reference Article.'

#         By 'citing,' we mean that the 'Text Referencing The Reference Article' refers to or aligns with the information, facts, or concepts in the 'Reference Article Text.' The match can be direct, paraphrased, or conceptually similar.

#         Guidelines:
#         - Extract ALL relevant parts of the 'Reference Article Text' (chunk) that is being referenced in the 'Text Referencing The Reference Article.'
#         - The match does not need to be exact; it can be a paraphrased or conceptually aligned statement.
#         - Consider not only direct references, but also cases where the 'Text Referencing The Reference Article' discusses related facts or concepts in different wording.
#         - If no part of the 'Reference Article Text' is cited, respond with 'no'.

#         Important Note:
#         There might be cases where the phrasing between the 'Reference Article Text' and the 'Text Referencing The Reference Article' differs, but the underlying concepts are aligned. For example, if the 'Reference Article Text' discusses gas production due to bacterial fermentation of lactose and the 'Text Referencing The Reference Article' discusses bloating and flatulence after lactose ingestion, these are conceptually aligned, and the relevant portion from the 'Reference Article Text' should be extracted.

#         Example of Matching Case:

#         Input:
#         'Reference Article Text: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Lactose intolerance. Lactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI). However, the two must not be confused and the causes of symptoms must be considered separately. Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).

#         Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

#         Output:
#         'Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).'

#         Example of Non-Matching Case (When to Respond with 'No'):

#         Input:
#         'Reference Article Text: Lactase persistence is common among populations of Northern European descent. The LCT −13’910:C/C genotype is associated with the ability to digest lactose in adulthood.

#         Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

#         Output:
#         'no'

#         Why this case results in 'no':
#         In this case, the 'Reference Article Text' discusses lactase persistence and a genetic factor related to lactose digestion, while the 'Text Referencing The Reference Article' discusses gas formation due to bacterial fermentation of lactose. These are different concepts, and no alignment exists between the two texts. Therefore, the correct response is 'no.'
        
#         Input:
#         Reference Article Text: {chunk}
#         Text Referencing The Reference Article: {ref}

#         Output:

#         """
# query = """
#         Compare the 'Reference Article Text' (which is a chunk of the reference article) to the 'Text Referencing The Reference Article' (which cites the reference article). Identify which parts of the 'Reference Article Text' are being cited or referenced by the 'Text Referencing The Reference Article.'

#         By 'citing,' we mean that the 'Text Referencing The Reference Article' refers to or aligns with the information, facts, or concepts in the 'Reference Article Text.' The match can be direct, paraphrased, or conceptually similar.

#         Guidelines:
#         - Extract the part of the 'Reference Article Text' (chunk) that is being referenced in the 'Text Referencing The Reference Article.'
#         - The match does not need to be exact; it can be a paraphrased or conceptually aligned statement.
#         - Consider not only direct references, but also cases where the 'Text Referencing The Reference Article' discusses related facts or concepts in different wording.
#         - If no part of the 'Reference Article Text' is cited, respond with 'no'.

#         Important Note:
#         There might be cases where the phrasing between the 'Reference Article Text' and the 'Text Referencing The Reference Article' differs, but the underlying concepts are aligned. For example, if the 'Reference Article Text' discusses gas production due to bacterial fermentation of lactose and the 'Text Referencing The Reference Article' discusses bloating and flatulence after lactose ingestion, these are conceptually aligned, and the relevant portion from the 'Reference Article Text' should be extracted.
        
#         Example of Matching Case:

#         Input:
#         'Reference Article Text: Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Lactose intolerance. Lactose malabsorption (LM) is a necessary precondition for lactose intolerance (LI). However, the two must not be confused and the causes of symptoms must be considered separately. Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).

#         Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

#         Output:
#         'Bacterial fermentation of lactose results in production of gases including hydrogen (H2), carbon dioxide (CO2), methane (CH4), and short-chain fatty acids (SCFA) that have effects on GI function (figure 1). Many individuals with LM have no symptoms after ingestion of a standard serving of dairy products (table 1), whereas others develop symptoms (‘intolerance’) such as abdominal pain, borborygmi (rumbling tummy), and bloating after lactose intake (figure 1).'

#         Example of Non-Matching Case (When to Respond with 'No'):

#         Input:
#         'Reference Article Text: Lactase persistence is common among populations of Northern European descent. The LCT −13’910:C/C genotype is associated with the ability to digest lactose in adulthood.

#         Text Referencing The Reference Article: The bacteria in the large intestine ferment lactose, resulting in gas formation, which can cause symptoms such as bloating and flatulence after lactose ingestion.'

#         Output:
#         'no'

#         Why this case results in 'no':
#         In this case, the 'Reference Article Text' discusses lactase persistence and a genetic factor related to lactose digestion, while the 'Text Referencing The Reference Article' discusses gas formation due to bacterial fermentation of lactose. These are different concepts, and no alignment exists between the two texts. Therefore, the correct response is 'no.'
#         """