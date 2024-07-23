import os
from openpyxl import Workbook
import unicodedata
from gpt_rag import *
import fitz  # PyMuPDF

def read_pdf_file_list():
    """Return the list of PDF file names."""
    return [
        "Aliment Pharmacol Ther - 2007 - LOMER - Review article  lactose intolerance in clinical practice   myths and realities.pdf",
        "Countryregionalandglobalestimates.pdf",
        "Effects_of_Prebiotic_and_Probiotic_Supplementation.pdf",
        "EFSA Journal - 2010 -  - Scientific Opinion on lactose thresholds in lactose intolerance and galactosaemia.pdf",
        "FermentedfoodsandprobioticsAnapproach.pdf",
        "heyman.pdf",
        "Kranen.pdf",
        "lactose_intolerance_an_update_on_its_pathogenesis_diagnosis_treatment.pdf",
        "lactoseandlactosederivatives.pdf",
        "lactosemalabsorptionandintolerance.pdf",
        "lactosemalabsorptionandpresumedrelateddisorders.pdf",
        "M47NHG-Standaard_Voedselovergevoeligheid.pdf",
        "managementandtreatmentoflactosemalabsorption.pdf",
        "updateonlactoseintoleranceandmalabsorption.pdf"
    ]

def get_txt_names():
    pdf_list = read_pdf_file_list()
    doc_files = [f"{i}.txt" for i in range(len(pdf_list))]

    return doc_files

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

def full_cycle(pdf,filename):
    filename=filename+".txt"
    p=extract_text_from_pdf(pdf)
    d=save_text_to_file(p,filename)
    filename=read_text_file(filename)

    return filename