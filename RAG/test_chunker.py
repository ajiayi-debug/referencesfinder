from semantic_router.encoders import AzureOpenAIEncoder
from dotenv import *
import os
import subprocess
from semantic_chunkers import StatisticalChunker, ConsecutiveChunker, CumulativeChunker

load_dotenv()

az_path = os.getenv("az_path")

# Fetch Azure OpenAI access token
result = subprocess.run([az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()

# Set environment variables
os.environ['AZURE_OPENAI_ENDPOINT'] = os.getenv('endpoint')
os.environ['AZURE_OPENAI_API_KEY'] = token
os.environ['AZURE_OPENAI_API_VERSION'] = os.getenv('ver')

encoder = AzureOpenAIEncoder(deployment_name=os.getenv('embed_model'), model='text-embedding-3-large', api_key=token, azure_endpoint=os.getenv('endpoint'), api_version=os.getenv('ver'))


with open('13.txt', 'r', encoding='utf-8') as f:
  content=f.read()

chunker = StatisticalChunker(encoder=encoder)

chunks = chunker(docs=[content])

# chunker.print(chunks[0])

# print(type(chunks[0]))
# print(dir(chunks[0]))

for chunk in chunks[0]:
  print(chunk.splits)
