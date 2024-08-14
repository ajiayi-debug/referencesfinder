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



load_dotenv()


az_path = os.getenv("az_path")

# Fetch Azure OpenAI access token
result = subprocess.run([az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()

# Set environment variables
os.environ['AZURE_OPENAI_ENDPOINT'] = os.getenv('endpoint')
os.environ['AZURE_OPENAI_API_KEY'] = token

# Set up your Azure OpenAI API key and Google Custom Search API credentials
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
google_api_key = os.getenv("googleapikey")
google_cse_id = os.getenv("googlecseid")
name=os.getenv("name")
ver=os.getenv("ver")
cert=os.getenv("cert")



# Initialize the AzureOpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("ver")
)


# Get names of all PDF articles
def naming(text):
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": "What is the name of the article? Return the name only."},
            {"role": "user", "content": [
                {"type": "text", "text": text},
                
                ]
            }
        ]
    )

    # Print the response
    return response.choices[0].message.content

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
    for i in range(len(processed_texts)):
        input_path = os.path.join(directory, processed_texts[i])
        with open(input_path, 'r', encoding='utf-8') as f:
            processed_text = f.read()
            cleaned_text = ''.join(char for char in processed_text if unicodedata.category(char)[0] != 'C')
        # text=read_text_file(input_path)
            name=naming(cleaned_text)
            processed_texts[i]=str(name)
    return processed_texts




system_prompt="In the following text, what are the full texts of each reference (can be multiple sentences) and the name of the reference articles? Format your response in this manner:[['The lactase activity is usually fully or partially restored during recovery of the intestinal mucosa.','Lactose intolerance in infants, children, and adolescents'],...]"


# Get the references and the cited articles' names in the main article
def get_references(text):
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": text},
                
                ]
            }
        ]
    )

    # Print the response
    return response.choices[0].message.content


# Get the text that the reference inb the main article is citing in the reference article
def similiar_ref(text,ref):
    query="You are a reference fact checker. You check if the reference can be found in the abstract of the article in terms of semantic meaning. If yes, you highlight the information in the abstract of the article. Output the semantically similiar information only. Don't output the Text Content (reference sentenceused to compare with the article)."
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": query},
            {"role": "user", "content": [
                {"type": "text", "text": f"Text Content: {text}, Article:{ref}"},
                # {"type": "text", "text": f"PDF:{ref}"}
                ]
            }
        ]
    )

    # Print the response
    return response.choices[0].message.content

#Clean up gpt 4o output in getting the text that the references in main articles are citing as the format can be off. 
def clean_responses(sentence):
    query="Tidy up the following text to output sentence(s). Dont include unnecessary jargons like Text Content and PDF. For example: '**PDF: ****Text on page 3: ****Malabsorption of lactose, resulting from the combination of lactase deficiency and lactose intake levels of more than 10–15 g per day, and giving symptoms of lactose intolerance have often led to the rejection of milk as a food and to discouragement of milk in food aid programs for the third world.**' becomes 'Malabsorption of lactose, resulting from the combination of lactase deficiency and lactose intake levels of more than 10–15 g per day, and giving symptoms of lactose intolerance have often led to the rejection of milk as a food and to discouragement of milk in food aid programs for the third world.'"
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": query},
            {"role": "user", "content": [
                {"type": "text", "text": f"The text is: {sentence}"},
                # {"type": "text", "text": f"PDF:{ref}"}
                ]
            }
        ]
    )

    # Print the response
    return response.choices[0].message.content



