import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import subprocess
import pandas as pd
import re
import tiktoken

load_dotenv()

az_path = os.getenv("az_path")

# Fetch Azure OpenAI access token
result = subprocess.run([az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()

# Set environment variables
os.environ['AZURE_OPENAI_ENDPOINT'] = os.getenv('endpoint')
os.environ['AZURE_OPENAI_API_KEY'] = token



client = AzureOpenAI(
  api_key = os.getenv("AZURE_OPENAI_API_KEY"),  
  api_version = os.getenv("ver"),
  azure_endpoint =os.getenv("AZURE_OPENAI_ENDPOINT") 
)

excel_file = 'processed_documents.xlsx'
df = pd.read_excel(excel_file)

def normalize_text(s, sep_token = " \n "):
  s = re.sub(r'\s+',  ' ', s).strip()
  s = re.sub(r". ,","",s)
  # remove all instances of multiple spaces
  s = s.replace("..",".")
  s = s.replace(". .",".")
  s = s.replace("\n", "")
  s = s.strip()
    
  return s

def split_text_by_page_marker(text: str):
    chunks = text.split('Text on page ')
    # Adding back the 'Text on page' marker to each chunk except the first one
    chunks = [chunks[0]] + ['Text on page ' + chunk for chunk in chunks[1:]]
    return chunks


df['Text Content']= df["Text Content"].apply(lambda x : normalize_text(x))
print(df.head())


# tokenizer = tiktoken.get_encoding("cl100k_base")
# df['n_tokens'] = df["Text Content"].apply(lambda x: len(tokenizer.encode(x)))
# df = df[df.n_tokens<8192]
# print(len(df))


response = client.embeddings.create(
    input = "Your text string goes here",
    model= os.getenv("embed_model")
)

#print(response.model_dump_json(indent=2))


