from pdf import *
from gpt_rag import *
from embedding import *
import ast
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from call_mongodb import *
from tqdm import tqdm

load_dotenv()
#main pdf
pdf_to_check = os.getenv("PDF")
uri = os.getenv("uri_mongo")
client = MongoClient(uri)
db = client['data']

#chunked and embedded original refs database, new database name to store output
def process_old_references(collection_processed_name, collection_name):
    output_directory = 'RAG'  # Fixed output directory
    pdf_to_check = os.getenv("PDF")
    
    # Get collections from MongoDB
    collection_processed = db[collection_processed_name]
    collection = collection_name

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
        similiar = retrieve_similar_text_threshold(pdf, code, 10, 0.5)  # return top n, >0.5 cosine similarity of each pdf name
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
                'reference article name': [code[1]], 
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