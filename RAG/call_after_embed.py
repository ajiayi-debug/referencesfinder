from pdf import *
from gpt_rag import *
from embedding import *
import ast
import pandas as pd
from dotenv import *
from pymongo import MongoClient
from call_mongodb import *
from tqdm import tqdm

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

    dfs = []
    for code in tqdm(codable, desc="Processing cos similiarity and pruning"):
        pdf = retrieve_pdf(df, code)
        similiar = retrieve_similiar_text_threshold(pdf, code, 10, 0.5)  # return top n, >0.5 cosine similiarity of each pdf name
        #list of chunks
        similiarcopy=similiar.copy()
        lstchunk=similiarcopy['Text Content'].tolist()
        # index_reassigned=ast.literal_eval(check_gpt(rearrange_list(code[0], lstchunk)))
        max_retries = 3  
        retry_delay = 1 
        attempt=0
        while attempt<max_retries:
            try:
                index_reassigned=ast.literal_eval(rank_and_check(code[0],lstchunk))
                print(index_reassigned)
                reset_index_df=similiar.reset_index(drop=True)
                similiar_rearranged=reset_index_df.iloc[index_reassigned]
                break
            except IndexError as e:
                print(f"IndexError: {e}. Attempt {attempt + 1} of {max_retries}. Retrying...")
                attempt += 1
                time.sleep(retry_delay)

        for index,row in similiar_rearranged.iterrows():
            textcontent=row['Text Content']
            cossim=row['similarities_text']
            getans = similiar_ref(code[0], textcontent)
            cleanans=clean_responses(getans)
        
            #Create a DataFrame for the current row and specify an index
            newrow = pd.DataFrame({'reference article name': [code[1]], 'Reference text in main article': [code[0]], 'Reference identified by gpt4o in chunk': [cleanans], 'Chunk': [textcontent], 'Cosine Similiarity': [cossim]})
            #newrow = pd.DataFrame({'reference article name': [code[1]], 'Reference text in main article': [code[0]], 'Chunk': [textcontent], 'Cosine Similiarity': [cossim]})
            dfs.append(newrow)
    
    # Concatenate all row DataFrames into one
    output_df = pd.concat(dfs, ignore_index=True)
    
    # Specify the file name and path
    final_ans = 'find_ref_new_embed_pruned_top10.xlsx'
    send_excel(output_df,output_directory,final_ans)
    




if __name__ == "__main__":
    main()