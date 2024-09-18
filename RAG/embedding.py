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
from tqdm import tqdm


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

tokenizer = tiktoken.get_encoding("cl100k_base")

# excel_file = 'processed.xlsx'
# df = pd.read_excel(excel_file)

""" call this function to read excel file """
def read_file(excel_file, directory):
    input_path = os.path.join(directory, excel_file)
    df=pd.read_excel(input_path)
    return df
#helper function
def normalize_text(s, sep_token = " \n "):
  s = re.sub(r'\s+',  ' ', s).strip()
  s = re.sub(r". ,","",s)
  # remove all instances of multiple spaces
  s = s.replace("..",".")
  s = s.replace(". .",".")
  s = s.replace("\n", "")
  s = s.strip()
    
  return s
#helper function
def split_text_by_page_marker(text: str):
  chunks = text.split('Text on page ')
  # Adding back the 'Text on page' marker to each chunk except the first one
  chunks = [chunks[0]] + ['Text on page ' + chunk for chunk in chunks[1:]]
  return 

""" call this function to split the text as well as normalize them """
def splitting(df, title):
    # Initialize tqdm for pandas inside the function
    tqdm.pandas(desc="Splitting and Normalizing text")
    
    # Use progress_apply to display the progress bar
    df[title] = df[title].progress_apply(lambda x: normalize_text(x))
    return df

#df['Text Content']= df["Text Content"].apply(lambda x : normalize_text(x))

""" Call this function to tokenize content  """
def tokenize(df, title):
    tqdm.pandas(desc='Tokenizing chunks')
    df['n_tokens']=df[title].progress_apply(lambda x: len(tokenizer.encode(x)))
    return df

# tokenizer = tiktoken.get_encoding("cl100k_base")
# df['n_tokens'] = df["Text Content"].apply(lambda x: len(tokenizer.encode(x)))

# helper function
def chunk_text(text, max_tokens):
    tokens = tokenizer.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text) 
    return chunks

""" Call this function to chunk the text according to tokenizer number (recco 8190 tokens) """
def chunking(df, title, tokens):
    tqdm.pandas(desc='chunking text for token limit')
    df['Text Chunks'] = df[title].progress_apply(lambda x: chunk_text(x, tokens))
    df = df.explode('Text Chunks').reset_index(drop=True)
    df['n_tokens'] = df["Text Chunks"].progress_apply(lambda x: len(tokenizer.encode(x)))
    return df


# df['Text Chunks'] = df["Text Content"].apply(lambda x: chunk_text(x, 8190))
# df = df.explode('Text Chunks').reset_index(drop=True)
# df['n_tokens'] = df["Text Chunks"].apply(lambda x: len(tokenizer.encode(x)))


#helper function
def generate_embeddings(text, model=os.getenv("embed_model")): # model = "deployment_name"
    embed=client.embeddings.create(input = [text], model=model).data[0].embedding
    return embed
""" Call this function to generate embeddings """
def embed(df):
    tqdm.pandas(desc="Generating embeddings")
    df['embed_v3'] = df["Text Chunks"].progress_apply(lambda x : generate_embeddings (x, model = os.getenv("embed_model")))
    #df['embed_name']=df['PDF File'].apply(lambda x : generate_embeddings (x, model = os.getenv("embed_model")))
    return df

#df['embed_v3'] = df["Text Chunks"].apply(lambda x : generate_embeddings (x, model = os.getenv("embed_model"))) 

""" Call this function to send embedded data to an excel file """
def send_excel(df,directory, filename):
    # os.makedirs(directory)
    output_path=os.path.join(directory,filename)
    df.to_excel(output_path, index=False)
    print(f'Data has been written to {output_path}')

#helper function
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
#helper function
def get_embedding(text, model=os.getenv("embed_model")): # model = "deployment_name"
    embed=client.embeddings.create(input = [text], model=model).data[0].embedding
    return embed

# def search_docs_names(df, user_query, top_n=4, to_print=True):
#     embedding = get_embedding(
#         user_query,
#         model=os.getenv("embed_model") # model should be set to the deployment name you chose when you deployed the text-embedding-ada-002 (Version 2) model
#     )
    
#     df["similarities_name"] = df.embed_name.apply(lambda x: cosine_similarity(x, embedding))
#     res = (
#         df.sort_values("similarities_name", ascending=False)
#         .head(top_n)
#     )
#     if to_print:
#         print(res) 
#     return res


#Helper function to convert dtype obj to dtype float
def convert_to_float_array(obj):
    """
    Convert an object (e.g., list or string representation of a list) to a numpy array of floats.
    """
    if isinstance(obj, str):
        # Convert string representation of a list to a list
        obj = eval(obj)
    return np.array(obj, dtype=float)


#helper function
def search_docs_text(df, user_query, top_n, to_print=True):
    df=df.copy()
    embedding = get_embedding(
        user_query,
        model=os.getenv("embed_model") # model should be set to the deployment name you chose when you deployed the model
    )
    df.loc[:, 'embed_v3'] = df['embed_v3'].apply(convert_to_float_array)
    df.loc[:,"similarities_text"] = df.embed_v3.apply(lambda x: cosine_similarity(x, embedding)) 
    
    res = (
        df.sort_values("similarities_text", ascending=False)
        .head(top_n)
    )
    # if to_print:
    #     print(res) 
    return res
#add extra threshold to above helper function
def search_docs_text_threshold(df, user_query, top_n, threshold, to_print=True):
    df=df.copy()
    embedding = get_embedding(
        user_query,
        model=os.getenv("embed_model") # model should be set to the deployment name you chose when you deployed the model
    )
    df.loc[:, 'embed_v3'] = df['embed_v3'].apply(convert_to_float_array)
    df.loc[:,"similarities_text"] = df.embed_v3.apply(lambda x: cosine_similarity(x, embedding)) 
    filtered_df = df[df["similarities_text"] > threshold]
    if filtered_df.empty:
        # If no document has a similarity above the threshold, return the top similarity
        top_similarity = df["similarities_text"].max()
        res = df[df["similarities_text"] == top_similarity]
    else:
        # Otherwise, return the top N documents above the threshold
        res = (
            filtered_df.sort_values("similarities_text", ascending=False)
            .head(top_n)
        )
    
    # if to_print:
    #     print(res) 
    return res
#helper function for regex
def normalize_string(s):
    return re.sub(r'\s+', '', s).lower()

""" Call this functon to focus on the pdf  """
#each input is an element containing [text,name, year]
def retrieve_pdf(df,name_and_text_and_year):
    name = normalize_string(name_and_text_and_year[1])
   
    # Apply normalization to the "PDF File" column
    df['normalized_pdf_file'] = df['PDF File'].apply(normalize_string)
    
    # Filter the DataFrame using the normalized values
    new_df = df[df['normalized_pdf_file'] == name]
    
    return new_df



""" Call this function to obtain top n similiar texts in abstract based on cosine similiarity. Output is a dataframe."""

def retrieve_similiar_text(new_df,name_and_text_and_year, top_n):
    text=name_and_text_and_year[0]
    sd=search_docs_text(new_df, text, top_n)
    return sd

""" Call this function to obtain top n and >0.5 similiar texts in abstract based on cosine similiarity. Output is a dataframe."""
def retrieve_similar_text_threshold(new_df, name_and_text, top_n, threshold):
    if new_df.empty:
        return None  # or return an empty list, DataFrame, or any other placeholder as needed

    text = name_and_text[0]
    sd = search_docs_text_threshold(new_df, text, top_n, threshold)
    return sd

def retrieve_similar_text_threshold_old(new_df, name_and_text, top_n, threshold):
    text = name_and_text[0]
    sd = search_docs_text_threshold(new_df, text, top_n, threshold)
    return sd

def retrieve_similar_text_threshold_text_only(new_df, text, top_n, threshold):
    sd = search_docs_text_threshold(new_df, text, top_n, threshold)
    return sd

#res = search_docs(df, "At birth, almost every infant produces enough lactase to digest the lactose in breast milk. The production of lactase decreases gradually after the age of 3 years.", top_n=4)

"""" Call this function to get top row of focused df to get top cosine similiarity for gpt to find the sentence with closest meaning OR Call this function to get Text content of each PDF (non-embed df)"""
def focus_on_best(df):
    ans=df.iloc[0]['Text Content']
    return ans



