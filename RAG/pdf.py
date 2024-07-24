import os
from openpyxl import Workbook
import unicodedata
from gpt_rag import *
import fitz  # PyMuPDF
import glob

def read_pdf_file_list(directory):
    abs_directory = os.path.abspath(directory)
    if not os.path.exists(abs_directory):
        raise FileNotFoundError(f"The directory {abs_directory} does not exist.")
    
    pdf_files = glob.glob(os.path.join(abs_directory, "*.pdf"))
    return pdf_files

def get_txt_names(directory):
    pdf_list = read_pdf_file_list(directory)
    doc_files = [f"{i}.txt" for i in range(len(pdf_list))]
    return doc_files

def extract_text_from_pdf(pdf_path):
    """
    Extract text from each page of a PDF file using PyMuPDF.
    
    Args:
    - pdf_path (str): Path to the PDF file.
    
    Returns:
    - list: List containing text extracted from each page.
    """
    pdf_document = fitz.open(pdf_path)
    extracted_text = []
    
    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)
        text = page.get_text()
        extracted_text.append(text)
    
    pdf_document.close()
    return extracted_text

def save_text(text_list, filename, output_dir):
    """
    Save extracted text to a .txt file in the specified output directory.
    
    Args:
        text_list (list): List containing text from each page.
        filename (str): Name of the output text file.
        output_dir (str): Directory to save the output text file.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Construct the full path to the output file
    output_file = os.path.join(output_dir, filename)
    
    with open(output_file, 'w', encoding='utf-8') as text_file:
        for page_number, text in enumerate(text_list):
            text_file.write(f"Text on page {page_number + 1}:\n{text}\n\n")



def full_cycle_specific(pdf,filename, output_dir):
    filename=filename+".txt"
    p=extract_text_from_pdf(pdf)
    d=save_text(p,filename,output_dir)
    # full_txt_path = os.path.join(output_dir, filename)
    # filename=read_text_file(full_txt_path)

    # return filename

def process_and_save_pdfs(pdf_list, output_dir='doc'):
    """
    Process each PDF file, save the processed text to the specified output directory.
    
    Args:
        pdf_list (list): List of PDF file paths.
        output_dir (str): Directory to save processed text files.
    """
    os.makedirs(output_dir, exist_ok=True)  # Ensure the output directory exists
    
    for i, pdf_path in enumerate(pdf_list):
        # Process the PDF and get the processed text
        file_content = full_cycle_specific(pdf_path, filename=str(i), output_dir=output_dir)
        
        # Optionally, you can print the content or do additional processing here
        
        

def read_processed_texts(directory,filenames):
    """
    Read the processed content from text files and return a list of cleaned texts.
    Args:
        directory (str): The directory where the text files are stored.

    Returns:
        list: A list of cleaned text contents.
    """

    processed_texts = []
    for filename in filenames:
        input_path = os.path.join(directory, filename)
        with open(input_path, 'r', encoding='utf-8') as f:
            processed_text = f.read()
            cleaned_text = ''.join(char for char in processed_text if unicodedata.category(char)[0] != 'C')
            processed_texts.append(cleaned_text)

    return processed_texts






def write_to_excel(pdf_list, processed_texts, output_directory, output_filename):
    """
    Write the PDF file names and their processed text contents to an Excel file.
    Args:
        pdf_list (list): List of PDF file names.
        processed_texts (list): List of cleaned text contents.
        output_directory (str): The directory where the Excel file should be saved.
        output_filename (str): The name of the output Excel file.
    """
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    output_path = os.path.join(output_directory, output_filename)
    
    workbook = Workbook()
    sheet = workbook.active

    # Add headers (optional)
    sheet['A1'] = 'PDF File'
    sheet['B1'] = 'Text Content'

    # Populate data into worksheet
    for index, pdf_name in enumerate(pdf_list, start=2):  # Start from row 2 for data
        sheet[f'A{index}'] = pdf_name
        sheet[f'B{index}'] = processed_texts[index - 2]  # Index adjusted for zero-based list

    workbook.save(output_path)
    print(f'Data has been written to {output_path}')

def extract_text_from_pdf(pdf_path):
    """
    Extract text from each page of a PDF file using PyMuPDF.
    
    Args:
    - pdf_path (str): Path to the PDF file.
    
    Returns:
    - list: List containing text extracted from each page.
    """
    pdf_document = fitz.open(pdf_path)
    extracted_text = []
    
    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)
        text = page.get_text()
        extracted_text.append(text)
    
    pdf_document.close()
    return extracted_text

def save_text_to_file(text_list, output_file):
    """
    Save extracted text to a .txt file.
    
    Args:
    - text_list (list): List containing text from each page.
    - output_file (str): Path to the output .txt file.
    """
    with open(output_file, 'w', encoding='utf-8') as text_file:
        for page_number, text in enumerate(text_list):
            text_file.write(f"Text on page {page_number + 1}:\n{text}\n\n")

def read_text_file(file_path):
    """
    Reads the contents of a text file and returns as a string.
    
    Args:
    - file_path (str): Path to the text file.
    
    Returns:
    - str: Contents of the text file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content


