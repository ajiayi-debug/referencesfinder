from pdf import *
from gpt_rag import *
from embedding import *
from dotenv import *
from pymongo import MongoClient
from call_mongodb import *

load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri)
db = 'data'
collection = 'processed'


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
   
    df['text_chunks'] = df['Text Content'].apply(chunk_text_by_page)
    
    
    df_exploded = df.explode('text_chunks').drop(columns=['Text Content'])
    
    # Rename the columns for clarity
    df_exploded.rename(columns={'text_chunks': 'Text Content'}, inplace=True)
    

    filepath='test_chunk.xlsx'

    df_exploded.to_excel(filepath, index=False, engine='openpyxl')

    
    
    """ records = df_exploded.to_dict(orient='records')
    #upsert_database_and_collection(uri, db, collection, records)
    replace_database_collection(uri, db, collection, records)
    print("Data sent to MongoDB Atlas.") """


if __name__ == "__main__":
    main()