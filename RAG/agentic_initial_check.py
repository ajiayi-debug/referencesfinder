from .gpt_rag_asyncio import call_get_ref_async
from .pdf import process_main_file
from .call_mongodb import replace_database_collection
import ast
import pandas as pd
import asyncio
from pymongo import MongoClient
from dotenv import load_dotenv
from .agent import *
from .mongo_client import MongoDBClient
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']


async def _get_statements_agentic_async(text):
    # initial_prompt=
    output = await call_get_ref_async(text)
    return output

def get_statements_agentic():
    # Wrapper to call async function from sync function
    text = process_main_file('extracted')
    output=asyncio.run(_get_statements_agentic_async(text))
    codable=ast.literal_eval(output)
    dfs=[]
    for code in codable:
        maintext=code[0]
        refname=code[1]
        date=code[2]
        author=code[3]
        newrow = pd.DataFrame({
                    'Reference article name': [refname], 
                    'Reference text in main article': [maintext], 
                    'Date': [date],
                    'Name of authors': [author]
                })
        dfs.append(newrow)
    df=pd.concat(dfs,ignore_index=True)
    print(df)
        
    records = df.to_dict(orient='records')
    replace_database_collection(uri, db.name, 'collated_statements_and_citations', records)
    print("Data sent to MongoDB Atlas.")
    


    