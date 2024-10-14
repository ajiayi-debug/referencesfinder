import requests
import urllib3
from fuzzywuzzy import fuzz  # For fuzzy matching
import pandas as pd
from embedding import *
from tqdm import tqdm
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi
from call_mongodb import *

load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']
collection="Extracted_Retracted"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fuzzy matching threshold (adjustable)
FUZZY_THRESHOLD = 80

# Fallback: Function to search for a DOI using fuzzy matching in Crossref API
def find_doi_in_crossref(paper):
    url = "https://api.crossref.org/works"
    params = {
        "query.title": paper["title"],
        "rows": 5  # Fetch top 5 results for comparison
    }
    response = requests.get(url, params=params, verify=False)
    
    try:
        data = response.json()  # Parse the response JSON
    except ValueError:
        return 'Error parsing JSON response'
    
    # Iterate over returned results and compare using fuzzy matching
    if isinstance(data, dict) and 'message' in data and 'items' in data['message']:
        for item in data['message']['items']:
            title = item.get('title', [None])[0]  # Get the first title in the list
            if title:
                similarity_score = fuzz.partial_ratio(title, paper["title"])
                if similarity_score >= FUZZY_THRESHOLD:
                    return item.get('DOI', 'No DOI found')  # Return the DOI of the closest match
    return 'No DOI found'

# Function to check if a paper has been retracted or corrected based on its DOI
def check_retractions_or_corrections(doi):
    if doi == 'No DOI found' or 'Error' in doi:
        return f"{doi}, unable to check retractions/corrections."
    
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url, verify=False)
    
    try:
        data = response.json()  # Parse the response JSON
    except ValueError:
        return 'Error parsing JSON response'
    
    # Ensure the response is a dictionary with 'message' key
    if isinstance(data, dict) and 'message' in data:
        if 'relation' in data['message']:
            relations = data['message']['relation']
            for relation_type, items in relations.items():
                for item in items:
                    if relation_type == 'is-retracted-by':
                        return f"Paper is retracted by: {item['id']}"
                    elif relation_type == 'is-corrected-by':
                        return f"Paper is corrected by: {item['id']}"
                    elif relation_type == 'is-updated-by':
                        return f"Paper is updated by: {item['id']}"
            return "No corrections or retractions found."
        else:
            return "No corrections or retractions found."
    return 'Unexpected response format'



def df_check(paper_metadata):
    papers = [{"title": item[1], "author": item[3], "year": item[2]} for item in paper_metadata]
    df = []
    for paper in tqdm(papers, desc="Checking for retractions or corrections"):
        print(f"Checking paper: {paper['title']}")
        
        doi = find_doi_in_crossref(paper)
        print(f"DOI from Crossref: {doi}")
        
        if doi and doi != "No DOI found":
            retraction_status = check_retractions_or_corrections(doi)
            print(f"Retraction/Correction Status: {retraction_status}\n")
        else:
            retraction_status = "No DOI available, skipping retraction check."
            print(retraction_status)
        
        newrow = pd.DataFrame({
            'Reference article name': [paper["title"]], 
            'DOI': [doi], 
            'Retraction/Correction Status': [retraction_status]
        })
        
        if retraction_status != "No corrections or retractions found.":
            df.append(newrow)
    
    # If df is empty, create an empty DataFrame with columns
    if df:
        df = pd.concat(df, ignore_index=True)
    else:
        # Create an empty DataFrame with the required columns
        df = pd.DataFrame(columns=["Reference article name", "DOI", "Retraction/Correction Status"])
    
    # Send the DataFrame to Excel, even if it's empty
    print("Sending DataFrame to Excel (even if empty)...")
    send_excel(df, 'RAG', 'crossref.xlsx')

    data_dict = df.to_dict("records")
    
    # Insert into MongoDB
    if data_dict:  # Only insert if there's data
        print("Inserting DataFrame into MongoDB...")
        records = data_dict
        replace_database_collection(uri, db.name, collection, records)
        print("Data inserted into MongoDB successfully.")
    else:
        print("No data to insert into MongoDB.")
