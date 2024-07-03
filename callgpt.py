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

perfect_prompt="What are the references in the text? list it out for me. Then, list out the texts that references these references."
user_input="What are the references in the text? list it out for me. Then, list out the texts that references these references. "
PDF="FC-Institute-Publication-on-Lactose-intolerance_2022.pdf"
text="extracted"
p=extract_text_from_pdf(PDF)
d=save_text_to_file(p,text)
text=read_text_file(text)




# Create a completion request
response = client.chat.completions.create(
    model="gpt-4o",  # Adjust the model name as needed
    temperature=0,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": [
            {"type": "text", "text": user_input + text},
            
            ]
        }
    ]
)

# Print the response
print(response.choices[0].message.content)