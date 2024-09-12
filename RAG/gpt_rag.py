import os
import subprocess
import requests
from googleapiclient.discovery import build
from dotenv import load_dotenv
from openai import AzureOpenAI
from bs4 import BeautifulSoup
import time
from googleapiclient.errors import HttpError
import pandas as pd
import unicodedata
import json
import logging


load_dotenv()


az_path = os.getenv("az_path")

# Fetch Azure OpenAI access token
result = subprocess.run([az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()

# Set environment variables
os.environ['AZURE_OPENAI_ENDPOINT'] = os.getenv('endpoint')
os.environ['AZURE_OPENAI_API_KEY'] = token


# Initialize the AzureOpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("ver")
)

def retry_on_exception(func, *args, max_retries=3, retry_delay=2, **kwargs):
    attempt = 0
    while attempt < max_retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            logging.error(f"Attempt {attempt} failed with error: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    logging.error(f"All {max_retries} attempts failed for {func.__name__}.")
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




system_prompt="In the following text, what are the full texts of each reference (can be multiple sentences), the name of the reference articles and the year articles were publiched? Format your response in this manner:[['The lactase activity is usually fully or partially restored during recovery of the intestinal mucosa.','Lactose intolerance in infants, children, and adolescents','2006' ],...]"


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


def rearrange_list(text, list):
    def func():
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": 'You are a semantic ranker. You rank the list according to how semantically similar the text in the list is to the text for comparison. Make sure that if the text for comparison is positive about a certain subject, the text in the list is ALSO positive about that SAME subject and VICE VERSA. You output the rank of the list as a list of indexes ONLY.'},
                {"role": "user", "content": [{"type": "text", "text": f"Text for comparison: {text}. List: {list}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)

def check_gpt(output):
    def func():
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": 'You check if the input is in the form of a list like e.g. [0,1,2,3,4,5]. If it is, output the input as it is ONLY...'},
                {"role": "user", "content": [{"type": "text", "text": f"Input: {output}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)



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

def clean_away_nonsemantic(text):
    def func():
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": 'When the text says anything related to no semantic meaning or similarity or anything related to information not begin found, output *. Else, output the text as it is.'},
                {"role": "user", "content": [{"type": "text", "text": f"Text:{text}"}]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)


def keyword_search(text):
    def func():
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": 'What are the keywords in the Text? take note these keywords will be used for a graph search in semantic scholar. Output the keywords ONLY'},
                {"role": "user", "content": [{"type": "text", "text": f"Text:{text}" }]}
            ]
        )
        return response.choices[0].message.content

    return retry_on_exception(func)


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