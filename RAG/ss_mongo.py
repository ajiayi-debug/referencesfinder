import requests
import os
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

def fetch_papers(query, api_key, max_results=100):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {"x-api-key": api_key}
    params = {"query": query, "limit": max_results}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def insert_papers_to_mongodb(papers, collection):
    for paper in papers.get('data', []):
        # Optional: Transform data as needed
        document = {
        "paper_id": paper.get('paperId'),
        "title": paper.get('title'),
        "abstract": paper.get('abstract'),
        "authors": paper.get('authors', []),
        "year": paper.get('year'),
        "citations": paper.get('citations', []),
        "url": paper.get('url'),
        "pdf_url": paper.get('pdfUrl'),  # Extract PDF URL if available
        "is_open_access": paper.get('isOpenAccess', False)  # This field may not exist in all metadata
    }
        collection.update_one({"paper_id": document["paper_id"]}, {"$set": document}, upsert=True)

def fetch_all_papers(query, api_key, max_results=100):
    all_papers = []
    offset = 0
    while len(all_papers) < max_results:
        papers_data = fetch_papers(query, api_key, max_results=100)
        all_papers.extend(papers_data.get('data', []))
        if len(papers_data.get('data', [])) < 100:
            break
        offset += 100
    return all_papers

# Connect to MongoDB Atlas
uri = os.getenv("uri_mongo")
client = MongoClient(uri)
db = client['data']  

collection= db['semantic scholar'] 

api_key=os.getenv('x-api-key')
papers_data = fetch_all_papers("lactose intolerance", api_key)
insert_papers_to_mongodb({"data": papers_data}, collection)
