import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import subprocess
import pandas as pd

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
print(df.head())

response = client.embeddings.create(
    input = "Your text string goes here",
    model= os.getenv("embed_model")
)

print(response.model_dump_json(indent=2))


