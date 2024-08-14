from pdf import *
from gpt_rag import *
from embedding import *
import ast
import pandas as pd
from dotenv import *
from pymongo import MongoClient
from call_mongodb import *

load_dotenv()
pdf_to_check=os.getenv("PDF")
uri = os.getenv("uri_mongo")
client = MongoClient(uri)
db = client['data']  
collection_processed = db['processed'] 
data='data'
collection='find_ref'



def main():
    text=full_cycle(pdf_to_check,filename="extracted")
    output=get_references(text)
    codable=ast.literal_eval(output)
    print(len(codable))
    documents= list(collection_processed.find({}, {'_id': 1, 'PDF File': 1, 'Text Content': 1}))
    df=pd.DataFrame(documents)
    
    # output_directory = 'RAG'
    # df=read_file("processed.xlsx",output_directory)

    
    dfs = []
    for code in codable:
        pdf = retrieve_pdf(df, code)
        #best = focus_on_best(pdf)
        combine=concat(pdf)

        getans = similiar_ref(code[0], combine)
        cleanans=clean_responses(getans)
        
        # Create a DataFrame for the current row and specify an index
        row = pd.DataFrame({'reference article name': [code[1]], 'Reference text in main article': [code[0]], 'Reference text in reference article': [cleanans]})
        
        dfs.append(row)
    
    # Concatenate all row DataFrames into one
    output_df = pd.concat(dfs, ignore_index=True)
    


    # Specify the file name and path
    final_ans = 'find_ref_test.xlsx'
    send_excel(output_df,"RAG",final_ans)
    
    records = output_df.to_dict(orient='records')
    #upsert_database_and_collection(uri, data, collection, records)
    """Only use this when database is already created and you want a fresh db """
    replace_database_collection(uri, data, collection, records)
    print("Data sent to MongoDB Atlas.")



if __name__ == "__main__":
    main()