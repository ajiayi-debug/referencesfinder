from pdf import *
from gpt_rag import *
from embedding import *
import ast
import pandas as pd
from dotenv import *
from pymongo import MongoClient
from call_mongodb import *
import tqdm

load_dotenv()
pdf_to_check=os.getenv("PDF")
uri = os.getenv("uri_mongo")
client = MongoClient(uri)
db = client['data']  
collection_processed = db['processed_and_embed'] 
data='data'
collection='find_ref_embed'

def main():
    output_directory = 'RAG'
    # df=read_file("test_embed_and_chunk.xlsx",output_directory)
    documents= list(collection_processed.find({}, {'_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks':1,'embed_v3':1 }))
    df=pd.DataFrame(documents)
    text=full_cycle(pdf_to_check,filename="extracted")
    output=get_references(text)
    codable=ast.literal_eval(output)
    len(codable)
    # turns out gpt 4o is better than cosine similiarity as the text chunks are still too long for accurate representation of vectors, so cosine similiarity is off. Still, we can keep the embbedded database for future references!
    
    dfs = []
    for code in tqdm(codable, desc="Findin"):
        pdf = retrieve_pdf(df, code)
        similiar = retrieve_similiar_text(pdf, code)  # return top 4 cosine similiarity of each pdf name
        
        for index,row in similiar.iterrows():
            textcontent=row['Text Content']
            cossim=row['similarities_text']
            getans = similiar_ref(code[0], textcontent)
            cleanans=clean_responses(getans)
        
            # Create a DataFrame for the current row and specify an index
            newrow = pd.DataFrame({'reference article name': [code[1]], 'Reference text in main article': [code[0]], 'Reference text in reference article': [cleanans], 'Chunk': [textcontent], 'Cosine Similiarity': [cossim]})
        
            dfs.append(newrow)
    
    # Concatenate all row DataFrames into one
    output_df = pd.concat(dfs, ignore_index=True)
    
    # Specify the file name and path
    final_ans = 'find_ref_new_embed.xlsx'
    send_excel(output_df,output_directory,final_ans)
    




if __name__ == "__main__":
    main()