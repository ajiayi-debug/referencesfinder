from pdf import *
from gpt_rag import *
from embedding import *
from dotenv import *
from pymongo import MongoClient
from call_mongodb import *
from semantic_chunking import *

load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri)
db = 'data'
collection1 = 'processed'
collection2 = 'processed_and_embed'


def main():
    pdf='text'
    pdf_list = read_pdf_file_list(pdf)
    directory = 'doc'  # Specify your directory where text files are stored
    filenames=get_txt_names(pdf)
    process_and_save_pdfs(pdf_list, output_dir='doc')
    processed_texts = read_processed_texts(directory,filenames)
    processed_name=get_names(filenames,directory)

    data = {'PDF File': processed_name, 'Text Content': processed_texts}
    df = pd.DataFrame(data)
   
    df['text_chunks'] = df['Text Content'].apply(semantic_chunk)
    
    
    df_exploded = df.explode('text_chunks').drop(columns=['Text Content'])
    
    # Rename the columns for clarity
    df_exploded.rename(columns={'text_chunks': 'Text Content'}, inplace=True)
    #embed 

    split_df=splitting(df_exploded,'Text Content')
    token_df=tokenize(split_df,'Text Content')
    chunki=chunking(token_df,'Text Content',8190)
    emb=embed(chunki)

    # filepath='test_chunk.xlsx'

    # df_exploded.to_excel(filepath, index=False, engine='openpyxl')

    # send_excel(emb, 'RAG', 'test_embed_and_chunk.xlsx')

    
    
    records1 = df_exploded.to_dict(orient='records')
    #upsert_database_and_collection(uri, db, collection, records)
    replace_database_collection(uri, db, collection1, records1)

    print("Data sent to MongoDB Atlas.")
    
    records2 = emb.to_dict(orient='records')
    #upsert_database_and_collection(uri, db, collection, records)
    replace_database_collection(uri, db, collection2, records2)

    print("Data sent to MongoDB Atlas.")


if __name__ == "__main__":
    main()