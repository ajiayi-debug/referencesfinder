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
from pdftotext import *


load_dotenv()
pdf=os.getenv("PDF")

PDF=[]


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


def streamline(output):
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": "return the full text referencing the references as well as the references (in their correct citation format) in this format: {[text 1, reference 1],[text 2, reference 2],...}. Dont bother about the mistakes. Only return in that format only. I want to use the output for coding."},
            {"role": "user", "content": [
                {"type": "text", "text": output},
                
                ]
            }
        ]
    )

    # Print the response
    return response.choices[0].message.content

def arrange(input,list):
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": "Arrange the references according to the list of names of PDFs. Make sure that each name has their own text (not the other way around). If the reference does not exist in the list, remove the reference. Keep the original format of the dictionary of lists. Only return the dictionary, do not include the words python or ```"},
            {"role": "user", "content": [
                {"type": "text", "text": input},
                {"type": "text", "text": list},
                
                ]
            }
        ]
    )

    # Print the response
    return response.choices[0].message.content

# Create a completion request
def checker(pdf,text):
    query="You are a reference fact checker. You check if the text content can be found in the PDF. If yes, you highlight the information in the PDF"
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model name as needed
        temperature=0,
        messages=[
            {"role": "system", "content": query},
            {"role": "user", "content": [
                {"type": "text", "text": text},
                {"type": "text", "text": pdf}
                ]
            }
        ]
    )

    # Print the response
    return response.choices[0].message.content

d=["Aliment Pharmacol Ther - 2007 - LOMER - Review article  lactose intolerance in clinical practice   myths and realities.pdf","Countryregionalandglobalestimates.pdf","Effects_of_Prebiotic_and_Probiotic_Supplementation.pdf","EFSA Journal - 2010 -  - Scientific Opinion on lactose thresholds in lactose intolerance and galactosaemia.pdf","FermentedfoodsandprobioticsAnapproach.pdf","heyman.pdf","Kranen.pdf","lactose_intolerance_an_update_on_its_pathogenesis_diagnosis_treatment.pdf","lactoseandlactosederivatives.pdf","lactosemalabsorptionandintolerance.pdf","lactosemalabsorptionandpresumedrelateddisorders.pdf","M47NHG-Standaard_Voedselovergevoeligheid.pdf","managementandtreatmentoflactosemalabsorption.pdf","updateonlactoseintoleranceandmalabsorption.pdf" ]
dstr=str(d)
Doc=[]
for i in range(len(d)):
    texts=full_cycle(d[i],filename=str(i))
    Doc.append(str(i)+".txt")

for filename in Doc:
    # Read the processed content from the file
    input_path = filename  # Assuming files are in the current directory
    with open(input_path, 'r', encoding='utf-8') as f:
        processed_text = f.read()
    
    # Write the processed content to the 'doc' directory
    output_path = os.path.join('doc', filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(processed_text)





main=full_cycle(pdf,filename="extracted")
output=request(main)
print(output)
sl=streamline(output)
arg=arrange(sl,dstr)
print(arg)
#Should I one by one check each element or shuld I insert ALL elements ?????