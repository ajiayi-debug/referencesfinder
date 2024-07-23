from pdf import *
from gpt_rag import *

def main():
    pdf_list = read_pdf_file_list()
    directory = 'doc'  # Specify your directory where text files are stored
    filenames=get_txt_names()
    processed_texts = read_processed_texts(directory,filenames)
    processed_name=get_names(filenames,directory)
    output_directory = 'RAG'  # Specify the directory where you want to save the Excel file
    output_filename = 'processed.xlsx'
    write_to_excel(processed_name, processed_texts, output_directory, output_filename)
    # text=full_cycle("FC-Institute-Publication-on-Lactose-intolerance_2022.pdf",filename="extracted")
    # output=get_references(text)
    # print(output)

if __name__ == "__main__":
    main()