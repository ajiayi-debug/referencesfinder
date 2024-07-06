import os
import certifi
import subprocess
import requests
from googleapiclient.discovery import build
from dotenv import load_dotenv
from openai import AzureOpenAI
from bs4 import BeautifulSoup


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

text="What is the weather today?"

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("ver")
)

response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": "Refine the query for a google search. For example, Query: Is Sam Altman fired? Refined Query: Sam Altman fired"},
            {"role": "user", "content": [
                {"type": "text", "text": text},
                
            ]
        }
    ]
)

output=response.choices[0].message.content

print(output)

def google_search(query, api_key, cse_id, num=1):
    service = build("customsearch", "v1", developerKey=api_key)
    result = service.cse().list(q=query, cx=cse_id, num=num).execute()
    return result['items']

gs=google_search(output,google_api_key,google_cse_id,num=1)
print(gs)

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

def summarize_content(content,qns):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Adjust the model name as needed
            temperature=0,
            messages=[
                {"role": "system", "content": f"Summarise the content to answer the question {qns}"},
                {"role": "user", "content": [
                    {"type": "text", "text": content},
                
                    ]
                }
            ]
        )
        return response.choices[0].message.content
    except requests.RequestException as e:
        print(f"Failed to summarize content: {e}")
        return ""

for result in gs:
    title = result['title']
    link = result['link']
    print(f"Fetching content from: {title} - {link}")
    content = fetch_web_content(link)
    content=summarize_content(content,text)
    print(content)
    
