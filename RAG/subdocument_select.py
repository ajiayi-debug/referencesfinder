import os
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm
from pdf import *
from gpt_rag import *
from embedding import *
from call_mongodb import *
from semantic_chunking import *
import ast

files_directory='text' 
collection='subdocument_retrieved'
extraction='main_paper_extracts'

def main():
    load_dotenv()
    uri = os.getenv("uri_mongo")
    db = 'data'
    
    directory = 'doc'  # Fixed directory

    pdf_list = read_pdf_file_list(files_directory)
    
    # Process and save PDFs
    process_and_save_pdfs(pdf_list, directory)
    filenames = get_txt_names(files_directory)

    processed_texts = read_processed_texts(directory, filenames)
    processed_name = get_names(filenames, directory)
    

    data = {'PDF File': processed_name, 'Text Content': processed_texts}
    df = pd.DataFrame(data)
    df['Subdocument']=df['Text Content'].apply(chunk_text_by_page)
    df=df.explode('Subdocument')
    df = df.reset_index(drop=True)
    tqdm.pandas(desc="Generating summaries for each subdocument ")
    df['Summary']=df['Subdocument'].progress_apply(summarise_subdocument)

    pdf_to_check = os.getenv("PDF")
    text = full_cycle(pdf_to_check, filename="extracted")
    output = get_references(text)
    #[ref,name,date]
    codable = ast.literal_eval(output)
    col=['Reference','Article Name', 'Year']
    code_df=pd.DataFrame(codable, columns=col)

    dfs=[]
    for code in tqdm(codable, desc='Retrieving by summary for each ref text and their respective articles'):
        pdf=retrieve_pdf(df,code)
        pdf.loc[:, 'Reference'] = code[0]
        

        tqdm.pandas(desc='Determining which summary to retrieve')
        pdf['Contains Reference'] = pdf.progress_apply(lambda row: locate_subdoc(row['Summary'], row['Reference']), axis=1)
        pdf['Contains Reference']=pdf['Contains Reference'].str.lower()
        pdf = pdf[pdf['Contains Reference'] == 'yes']
        pdf = pdf.reset_index(drop=True)
        tqdm.pandas(desc='Chunking retrieved subdocuments (based on summary) by semantic chunking')
        pdf['Text Chunks'] = pdf['Subdocument'].progress_apply(semantic_chunk)
        df_exploded = pdf.explode('Text Chunks')
        dfs.append(df_exploded)
        
        # # Embed
        # split_df = splitting(df_exploded, 'Text Chunks')
        # token_df = tokenize(split_df, 'Text Chunks')
        # chunki = chunking(token_df, 'Text Chunks', 8190)
        # emb=embed(chunki)

        # #calculate cos sim
        # similiar = retrieve_similar_text_threshold(emb, code, 10, 0.5)
        # dfs.append(similiar)
    output_df = pd.concat(dfs, ignore_index=True)

    send_excel(output_df,'RAG','data.xlsx')
    send_excel(code_df, 'RAG', 'main_paper_extract.xlsx')

    # Convert DataFrames to records
    records = output_df.to_dict(orient='records')
    code_record=code_df.to_dict(orient='records')

    # Save data to MongoDB
    print("Sending data to MongoDB Atlas...")

    # Send all records at once for collection
    replace_database_collection(uri, db, collection, records)
    print(f"Data sent to MongoDB Atlas for collection: {collection}")

    replace_database_collection(uri, db, extraction, code_record)
    print(f"Data sent to MongoDB Atlas for collection: {extraction}")

    delete_folder(directory)


if __name__ == "__main__":
    # This block will only execute if the script is run directly
    main()