import os
from openai import AzureOpenAI
from environment import endpoint,tok
from pdftotext import extract_text_from_pdf, save_text_to_file, read_text_file


os.environ['AZURE_OPENAI_ENDPOINT'] = endpoint
os.environ['AZURE_OPENAI_API_KEY'] = tok

# Initialize the AzureOpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version="2024-02-01"
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