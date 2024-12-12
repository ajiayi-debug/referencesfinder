from .pdf import *
from .gpt_rag import *
from .embedding import *
import ast
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from .call_mongodb import *
from tqdm import tqdm
import certifi
from .gpt_rag_asyncio import *
import asyncio
from .mongo_client import MongoDBClient

load_dotenv()
#main pdf
pdf_to_check = os.getenv("PDF")
uri = os.getenv("uri_mongo")
client = MongoDBClient.get_client()
db = client['data']

#chunked and embedded original refs database, new database name to store output
def process_old_references(collection_processed_name, collection_name):
    pdf_to_check = os.getenv("PDF")
    
    # Get collections from MongoDB
    collection_processed = db[collection_processed_name]

    # Fetch documents from MongoDB
    documents = list(collection_processed.find({}, {
        '_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks': 1, 'embed_v3': 1
    }))
    df = pd.DataFrame(documents)
    
    # Perform full cycle and get references
    text = full_cycle(pdf_to_check, filename="extracted")
    output = get_references(text)
    codable = ast.literal_eval(output)

    dfs = []
    for code in tqdm(codable, desc="Processing cosine similarity, re-ranking and pruning"):
        pdf = retrieve_pdf(df, code)
        similiar = retrieve_similar_text_threshold_old(pdf, code, 10, 0.5)  # return top n, >0.5 cosine similarity of each pdf name
        lstchunk = similiar['Text Content'].tolist()
        date = int(code[2])
        index_reassigned = ast.literal_eval(rank_and_check(code[0], lstchunk))
        reset_index_df = similiar.reset_index(drop=True)
        similiar_rearranged = reset_index_df.iloc[index_reassigned]
        
        temp_dfs = []
        for index, row in similiar_rearranged.iterrows():
            textcontent = row['Text Content']
            cossim = row['similarities_text']
            getans = similiar_ref(code[0], textcontent)
            cleanans = clean_responses(getans)
            
            # Create a DataFrame for the current row
            newrow = pd.DataFrame({
                'Reference article name': [code[1]], 
                'Reference text in main article': [code[0]], 
                'Reference identified by gpt4o in chunk': [cleanans], 
                'Chunk': [textcontent], 
                'Cosine Similarity': [cossim],
                'Date': [date]
            })
            temp_dfs.append(newrow)
        
        if temp_dfs:
            combined_temp_dfs = pd.concat(temp_dfs, ignore_index=True)
            top_rows = combined_temp_dfs.head(3)
            dfs.append(top_rows)
    
    # Concatenate all row DataFrames into one
    output_df = pd.concat(dfs, ignore_index=True)
    
    # # Save results to Excel and MongoDB
    # final_ans = 'find_ref_new_embed_pruned_top3_clean_test_test.xlsx'
    # send_excel(output_df, output_directory, final_ans)

    records = output_df.to_dict(orient='records')
    replace_database_collection(uri, db.name, collection_name, records)

    print("Data sent to MongoDB Atlas.")

def process_new_references(collection_processed_name, new_collection_name, collection_found):
    output_directory = 'backend'  # Fixed output directory
    
    # Get collections from MongoDB
    collection_processed = db[collection_processed_name]
    collection_f=db[collection_found]
    # Fetch documents from MongoDB
    documents1 = list(collection_processed.find({}, {'_id': 1, 'PDF File': 1, 'Text Content': 1, 'n_tokens': 1, 'Text Chunks': 1, 'embed_v3': 1 }))
    df = pd.DataFrame(documents1)

    documents2=list(collection_f.find({},{'_id': 1, 'Title of original reference article': 1, 'Text in main article referencing reference article': 1, 'Year reference article released': 1, 'Keywords for graph paper search': 1, 'Paper Id of new reference article found': 1, 'Title of new reference article found': 1, 'Year new reference article found published': 1, 'downloadable': 1, 'externalId_of_undownloadable_paper': 1, 'reason_for_failure': 1, 'pdf_url':1}))

    df_found=pd.DataFrame(documents2)
    df=replace_pdf_file_with_title(df, df_found)
    df_found=update_downloadable_status_invalid(df_found)
    df_found = df_found[df_found['downloadable'] != 'no']
    df_found = df_found[df_found['Paper Id of new reference article found'] != '']
    
    codable=[]
    for index, row in df_found.iterrows():
        text=row['Text in main article referencing reference article']
        title=row['Title of new reference article found']
        year=row['Year new reference article found published']
        codable.append([text,title,year])
        dfs = []
    for code in tqdm(codable, desc="Processing cosine similarity, re-ranking and pruning"):
        pdf = retrieve_pdf(df, code)
        print(code[1])
        
        # Retrieve similar texts with threshold
        similiar = retrieve_similar_text_threshold(pdf, code, 10, 0.5)
        
        # Only proceed if similiar is not None and contains 'Text Content'
        if similiar is not None and 'Text Content' in similiar.columns:
            lstchunk = similiar['Text Content'].tolist()
            date = int(code[2])
            index_reassigned = ast.literal_eval(rank_and_check(code[0], lstchunk))
            
            # Reset index for a clean state
            reset_index_df = similiar.reset_index(drop=True)
            
            # Ensure indices are within bounds
            max_index = len(reset_index_df) - 1
            valid_indices = [i for i in index_reassigned if 0 <= i <= max_index]
            
            if valid_indices:
                # Apply valid indices to the DataFrame
                similiar_rearranged = reset_index_df.iloc[valid_indices]
                
                temp_dfs = []
                for index, row in similiar_rearranged.iterrows():
                    textcontent = row['Text Content']
                    cossim = row['similarities_text']
                    getans = similiar_ref(code[0], textcontent)
                    cleanans = clean_responses(getans)
                    
                    # Create DataFrame for each row
                    newrow = pd.DataFrame({
                        'Reference article name': [code[1]], 
                        'Reference text in main article': [code[0]], 
                        'Reference identified by gpt4o in chunk': [cleanans], 
                        'Chunk': [textcontent], 
                        'Cosine Similarity': [cossim],
                        'Date': [date]
                    })
                    temp_dfs.append(newrow)
                
                if temp_dfs:
                    combined_temp_dfs = pd.concat(temp_dfs, ignore_index=True)
                    top_rows = combined_temp_dfs.head(3)
                    dfs.append(top_rows)
            else:
                print(f"All indices are out-of-bounds for code: {code[1]}")
                continue  # Skip processing if there are no valid indices
        else:
            print(f"Skipping processing as download is missing (not downloadable) for {code[1]}")
            continue
    # Concatenate all row DataFrames into one
    output_df = pd.concat(dfs, ignore_index=True)
    
    # Save results to Excel and MongoDB
    final_ans = 'new_refs_final_ans.xlsx'
    send_excel(output_df, output_directory, final_ans)

    final_ans='clean.xlsx'
    send_excel(df_found,output_directory, final_ans)

    records = output_df.to_dict(orient='records')
    replace_database_collection(uri, db.name, new_collection_name, records)

    print("Data sent to MongoDB Atlas.")

def get_statements():
    # Wrapper to call async function from sync function
    async def _get_statements_async():
        text = process_main_file('extracted')
        output = await call_get_ref_async(text)
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
    # Use asyncio.run to execute the async function
    return asyncio.run(_get_statements_async())


    