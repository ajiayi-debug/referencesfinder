import os
import certifi
import subprocess
import requests
from googleapiclient.discovery import build
from dotenv import load_dotenv
from openai import AzureOpenAI
from bs4 import BeautifulSoup
import time
from googleapiclient.errors import HttpError
import pandas as pd


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


system_prompt="You are in charge of updating PDFs for the company. In the following text, what are the references in the text? List out the full references. Then, list out the full texts that references these references according to page number. Make sure to state any mistakes in the referencing such as duplicate referencing or unused referencing."

edit="If the updated references debunks the text, add on to the previous text of the latest citations debunking the previous citation's claims. Make sure to retain the previous text as much as possible."



# Create a completion request
def request(text):
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




def findref(references):
    response = client.chat.completions.create(
            model="gpt-4o",  # Adjust the model name as needed
            temperature=0,
            messages=[
                {"role": "system", "content": "Refine the query for a google search of related references in order to update them such that it supports (or debunks) the related texts that used the references. As your knowledge is cut off from 2023, just say latest update instead of year in the queries. Return the queires in list form such that I can iterate through with code. For example, [query1,query2,...]. No extra words ."},
                {"role": "user", "content": [
                    {"type": "text", "text": references},
                
                ]
            }
        ]
    )

    output=response.choices[0].message.content
    return output

def google_search(query, num=1, max_retries=3):
    service = build("customsearch", "v1", developerKey=google_api_key)
    retries = 0
    while retries < max_retries:
        try:
            result = service.cse().list(q=query, cx=google_cse_id, num=num).execute()
            return result['items']
        except HttpError as e:
            print(f"HTTP error occurred: {e}")
            retries += 1
            time.sleep(5)  # Wait for 5 seconds before retrying
        except Exception as e:
            print(f"Error occurred: {e}")
            retries += 1
            time.sleep(5)  # Wait for 5 seconds before retrying
    
    print(f"Failed to retrieve search results for query: {query}")
    return []



def fetch_web_content(url):
    try:
        response = requests.get(url, verify=False)  # Set verify=True for SSL certificate verification
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        text = soup.get_text(separator=' ', strip=True)
        return text
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return ""

# def summarize_content(content):
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o",  # Adjust the model name as needed
#             temperature=0,
#             messages=[
#                 {"role": "system", "content": f"Summarise the content."},
#                 {"role": "user", "content": [
#                     {"type": "text", "text": content},
                
#                     ]
#                 }
#             ]
#         )
#         return response.choices[0].message.content
#     except requests.RequestException as e:
#         print(f"Failed to summarize content: {e}")
#         return ""

def convert_to_excel(excel_data):
    df = pd.DataFrame(excel_data)
    excel_filename = "output.xlsx"
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    print(f"Summarized content saved to '{excel_filename}'")
    return excel_filename


    




# def get_summary_of_existing(ref):
#     excel_data=[]

#     for r in ref:
#         search_results=google_search(r)
#         if search_results:
#             # Fetch content from the first search result URL
#             first_result_url = search_results[0]['link']
#             content = fetch_web_content(first_result_url)
            
#             if content:
#                 # Summarize the fetched content
#                 summarized_content = summarize_content(content)
#                 print(f"Summarized content for query '{r}':\n{summarized_content}")
#                 excel_data.append({"Query": r, "Summarized Content": summarized_content})
#             else:
#                 print(f"Failed to fetch content from {first_result_url}")
#         else:
#             print(f"No search results found for query '{r}'")
#     if excel_data:
#         df = pd.DataFrame(excel_data)
#         excel_filename = "output.xlsx"
#         df.to_excel(excel_filename, index=False, engine='openpyxl')
#         print(f"Summarized content saved to '{excel_filename}'")