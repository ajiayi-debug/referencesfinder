from .pdf import process_main_file
from .call_mongodb import replace_database_collection
import ast
import pandas as pd
import asyncio
from pymongo import MongoClient
from dotenv import load_dotenv
from .agent import get_statements_async, check_statement_output,effectiveness_state_extraction,evaluator_extractor,extract_no_format,check_extract_no_format,format_extract,check_only_statement_output,edit_mistakes_in_output
from .mongo_client import MongoDBClient
import os
import certifi
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']


def processor(output,text,c=10):
    count=c
    prompt="In the following text, what are the full texts of each reference (can be multiple sentences), the name of the reference articles, the year the articles were published and the author(s) of the articles? Format your response in this manner:[['The lactase activity is usually fully or partially restored during recovery of the intestinal mucosa.','Lactose intolerance in infants, children, and adolescents','2006','Heyman M.B' ],...]"
    evaluate=asyncio.run(check_only_statement_output(output,text))
    print(evaluate)
    effectiveness_state_extraction(evaluate,prompt,'extractor_prompt')
    while count>0 and not evaluate=='Y':
        prompt=evaluator_extractor(prompt,output,text,'extractor_prompt',evaluate)
        output=asyncio.run(get_statements_async(text,prompt=prompt))
        print(output)
        evaluate=asyncio.run(check_only_statement_output(output,text))
        print(evaluate)
        effectiveness_state_extraction(evaluate,prompt,'extractor_prompt')
        count-=1
    print(f'Retried a total of {c-count} times.')
    return output

def process(output,text,c=3):
    count=c
    #take note if got mistakes or not
    evaluate=asyncio.run(check_statement_output(output,text))
    #if there is mistakes
    while count>0 and not evaluate=='Y':
        #extract the corrected output
        output=asyncio.run(edit_mistakes_in_output(evaluate))
        #evaluate corrected output
        evaluate=asyncio.run(check_statement_output(output,text))
        print(output)
        print(evaluate)
        count-=1
    print(f'Retried a total of {c-count} times.')
    return output
def get_statements_agentic():
    # Wrapper to call async function from sync function
    text = process_main_file('extracted')
    initial_output=asyncio.run(get_statements_async(text))
    #output=processor(initial_output,text)
    output=process(initial_output,text)
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
    


    