import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import subprocess
import pandas as pd
import re
import tiktoken
import numpy as np
import re
from num2words import num2words

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



tokenizer = tiktoken.get_encoding("cl100k_base")
df['n_tokens'] = df["Text Content"].apply(lambda x: len(tokenizer.encode(x)))
# df = df[df.n_tokens<8192]
# print(len(df))

def chunk_text(text, max_tokens):
    tokens = tokenizer.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text)
    return chunks

df['Text Chunks'] = df["Text Content"].apply(lambda x: chunk_text(x, 8190))
df = df.explode('Text Chunks').reset_index(drop=True)
df['n_tokens'] = df["Text Chunks"].apply(lambda x: len(tokenizer.encode(x)))

# print(df)

# for index, row in df.iterrows():
#     print(f"Chunk {index} token length: {row['n_tokens']}")

# def embed(text):
#   response = client.embeddings.create(
#     input = text,
#     model= os.getenv("embed_model")
#   )
#   return response.model_dump_json(indent=2)

def generate_embeddings(text, model=os.getenv("embed_model")): # model = "deployment_name"
    return client.embeddings.create(input = [text], model=model).data[0].embedding

df['ada_v2'] = df["Text Chunks"].apply(lambda x : generate_embeddings (x, model = os.getenv("embed_model"))) 

# for text in df["Text Chunks"]:
#   e=embed(text)
#   print(e)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_embedding(text, model=os.getenv("embed_model")): # model = "deployment_name"
    return client.embeddings.create(input = [text], model=model).data[0].embedding

def search_docs(df, user_query, top_n=4, to_print=True):
    embedding = get_embedding(
        user_query,
        model=os.getenv("embed_model") # model should be set to the deployment name you chose when you deployed the text-embedding-ada-002 (Version 2) model
    )
    df["similarities"] = df.ada_v2.apply(lambda x: cosine_similarity(x, embedding))

    res = (
        df.sort_values("similarities", ascending=False)
        .head(top_n)
    )
    if to_print:
        print(res) 
    return res


res = search_docs(df, "At birth, almost every infant produces enough lactase to digest the lactose in breast milk. The production of lactase decreases gradually after the age of 3 years.", top_n=4)


