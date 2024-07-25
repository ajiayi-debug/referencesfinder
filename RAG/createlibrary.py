from pdf import *
from gpt_rag import *
from embedding import *

def main():
    pdf='text'
    pdf_list = read_pdf_file_list(pdf)
    directory = 'doc'  # Specify your directory where text files are stored
    filenames=get_txt_names(pdf)
    process_and_save_pdfs(pdf_list, output_dir='doc')
    processed_texts = read_processed_texts(directory,filenames)
    processed_name=get_names(filenames,directory)
    output_directory = 'RAG'  # Specify the directory where you want to save the Excel file
    output_filename = 'processed.xlsx'
    write_to_excel(processed_name, processed_texts, output_directory, output_filename)
    embed_filename="embedded.xlsx"
    content='Text Content'
    df=read_file(output_filename,output_directory)
    split_df=splitting(df,content)
    token_df=tokenize(split_df,content)
    chunki=chunking(token_df,content,8190)
    emb=embed(chunki)
    send_embed_excel(emb, output_directory, embed_filename)




if __name__ == "__main__":
    main()