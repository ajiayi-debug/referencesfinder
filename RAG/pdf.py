import os
from gpt_rag import *
from openpyxl import Workbook
import unicodedata
from gpt_rag import *
import fitz  # PyMuPDF
import glob
import re
import os
from dotenv import *
import pandas as pd
import shutil
from typing import AsyncGenerator, Generator, Iterable, TypeVar, Union, List, Dict, Any, Optional
from pathlib import Path
load_dotenv()

#get list of pdf file location in the directory
def read_pdf_file_list(directory):
    abs_directory = os.path.abspath(directory)
    if not os.path.exists(abs_directory):
        raise FileNotFoundError(f"The directory {abs_directory} does not exist.")
    
    pdf_files = glob.glob(os.path.join(abs_directory, "*.pdf"))
    return pdf_files

#rename the files according to numbers for further processing
def get_txt_names(directory):
    pdf_list = read_pdf_file_list(directory)
    doc_files = [f"{i}.txt" for i in range(len(pdf_list))]
    return doc_files

def get_txt_names_exactly(directory):
    # List all .txt files in the directory
    txt_files = [f for f in os.listdir(directory) if f.endswith('.txt')]
    return txt_files


def extract_text_from_pdf_specific(pdf_path):
    """
    Extract text from each page of a PDF file using PyMuPDF.
    
    Args:
    - pdf_path (str): Path to the PDF file.
    
    Returns:
    - list: List containing text extracted from each page, or None if the file is invalid.
    """
    try:
        pdf_document = fitz.open(pdf_path)
        extracted_text = []
        
        for page_number in range(len(pdf_document)):
            page = pdf_document.load_page(page_number)
            text = page.get_text()
            extracted_text.append(text)
        
        pdf_document.close()
        return extracted_text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return None
    


def invalid_pdf(pdf_path):
    text_list = extract_text_from_pdf_specific(pdf_path)
    invalid_pdfs_dir='invalid_pdfs'
    if text_list is None:
        # Move the invalid PDF if extraction failed
        move_invalid_pdf(pdf_path, invalid_pdfs_dir)

def process_invalid_pdfs(pdf_list):
    """
    Process each PDF file in the list and move invalid ones.
    
    Args:
    - pdf_list (list): List of PDF file paths.
    """
    for pdf_path in pdf_list:
        invalid_pdf(pdf_path)

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


# For reference files
def full_cycle_specific(pdf_path, filename, output_dir, invalid_pdfs_dir='invalid_pdfs'):
    """
    Process a PDF file: extract text, save to .txt, and move invalid files.
    
    Args:
    - pdf_path (str): Path to the PDF file.
    - filename (str): Base filename for the output text file (without extension).
    - output_dir (str): Directory to save the output text file.
    - invalid_pdfs_dir (str): Directory to move invalid PDF files.
    """
    # Extract text from the PDF
    text_list = extract_text_from_pdf_specific(pdf_path)
    
    if text_list is None:
        # Move the invalid PDF if extraction failed
        move_invalid_pdf(pdf_path, invalid_pdfs_dir)
    else:
        # Save the extracted text to a file
        save_text(text_list, f"{filename}.txt", output_dir)

def process_and_save_pdfs(pdf_list, output_dir):
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
    Read the processed content from text files and return a list of cleaned texts (each element comes from 1 .txt file).
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

#Create a function to send pdf file from frontend to backend

def process_main_file(filename):
    # Get the name of the single file in the directory
    files = os.listdir('main')
    if len(files) != 1:
        raise ValueError("Directory must contain exactly one file.")
    
    pdf_path = Path('main') / files[0]
    
    # Call the full_cycle function with the file path and desired filename
    result = full_cycle(pdf_path, filename)


    return result

# For main text
def full_cycle(pdf,filename):
    filename=filename+".txt"
    p=extract_text_from_pdf(pdf)
    d=save_text_to_file(p,filename)
    filename=read_text_file(filename)

    return filename



def chunk_text_by_page(text):
    """
    Chunk the text based on page numbers.
    Args:
        text (str): The text to chunk.
    Returns:
        list: A list of text chunks.
    """
    pattern = r'(?=Text on page \d+:)'
    chunks = re.split(pattern, text)
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    
    # Ensure consistency in chunk formatting
    for i in range(len(chunks)):
        if not chunks[i].startswith('Text on page'):
            chunks[i] = f'Text on page {i+1}:\n{chunks[i]}'
    
    return chunks

def concat(df):
    s = ""
    for d in df["Text Content"]:
        s += d + " "
    return s.strip()

def update_downloadable_status(df: pd.DataFrame, pdf_folder: str) -> pd.DataFrame:
    """
    Update the 'downloadable' column in the DataFrame based on whether the paper ID has a corresponding PDF file in the folder.

    :param df: DataFrame containing the paper IDs.
    :param pdf_folder: Folder path where the PDF files are stored.
    :return: Updated DataFrame with 'downloadable' column.
    """
    # List all PDF files in the folder and remove the '.pdf' extension
    pdf_files = [os.path.splitext(file)[0] for file in os.listdir(pdf_folder) if file.lower().endswith('.pdf')]

    # Create a set of PDF file names for faster lookup
    pdf_file_set = set(pdf_files)

    # Check if 'downloadable' column exists, if not, add it
    if 'downloadable' not in df.columns:
        df['downloadable'] = 'no'
    else:
        # Ensure column is initialized to 'no'
        df['downloadable'] = 'no'

    # Update 'downloadable' column based on whether the paper ID is in the PDF file set
    df.loc[df['Paper Id of new reference article found'].isin(pdf_file_set), 'downloadable'] = 'yes'

    return df




#move ext files to papers, keeping a copy in old directory

def move_pdf_files(source_folder: str, destination_folder: str):
    # Check if the source folder exists
    if not os.path.exists(source_folder):
        print(f"Source folder '{source_folder}' does not exist. Creating the folder.")
        os.makedirs(source_folder)
        return

    # Create destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)

    # Loop through all files in the source folder
    for filename in os.listdir(source_folder):
        if filename.endswith('.pdf'):
            source_path = os.path.join(source_folder, filename)
            destination_path = os.path.join(destination_folder, filename)
            
            if validate_pdf(source_path):
                # If the PDF is valid, move it to the destination folder
                shutil.copy2(source_path, destination_path)
                print(f"Moved valid external PDF: {filename}")
            else:
                # If the PDF is invalid, you can choose to ignore it
                print(f"Ignored invalid PDF: {filename}")

#move completedly based on type of file (whether valid pdf or not)
def move_pdf_files_completedly(source_folder: str, destination_folder: str, invalid_folder: str):
    """
    Move PDF files from the source folder to the destination folder or invalid folder based on their validity.
    
    Args:
    - source_folder (str): Directory containing the source PDF files.
    - destination_folder (str): Directory to move the valid PDF files.
    - invalid_folder (str): Directory to move invalid PDF files.
    """
    # Create destination folders if they don't exist
    os.makedirs(destination_folder, exist_ok=True)
    os.makedirs(invalid_folder, exist_ok=True)

    # Loop through all files in the source folder
    for filename in os.listdir(source_folder):
        if filename.endswith('.pdf'):
            source_path = os.path.join(source_folder, filename)
            if validate_pdf(source_path):
                # Move the PDF to the destination folder, overwriting if it exists
                destination_path = os.path.join(destination_folder, filename)
                shutil.move(source_path, destination_path)
                print(f"Moved valid PDF: {filename}")
            else:
                # Move the invalid PDF to the invalid folder
                invalid_path = os.path.join(invalid_folder, filename)
                shutil.move(source_path, invalid_path)
                print(f"Moved invalid PDF to invalid folder: {filename}")

#just moving files completedly if pdf and valid
def move_files(source_folder: str, destination_folder: str):
    # Check if the source folder exists
    if not os.path.exists(source_folder):
        print(f"Source folder '{source_folder}' does not exist. Creating the folder.")
        os.makedirs(source_folder)
        return

    # Create destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)

    # Loop through all files in the source folder
    for filename in os.listdir(source_folder):
        if filename.endswith('.pdf'):
            print(f'Moving {filename} from {source_folder} to {destination_folder}')
            source_path = os.path.join(source_folder, filename)
            destination_path = os.path.join(destination_folder, filename)
            
            if validate_pdf(source_path):
                # If the PDF is valid, move it to the destination folder
                shutil.move(source_path, destination_path)
                print(f"Moved valid external PDF: {filename}")
            else:
                # If the PDF is invalid, you can choose to ignore it
                print(f"Ignored invalid PDF: {filename}")
    print('Moved new-found papers to main papers directory.')

#check if each iteration same
def validate_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return False
        return True
    except Exception as e:
        print(f"Failed to validate PDF: {e}")
        return False

#add column called external id to dataframe, then only input ext id if paper id matches (input is list of list of external id and paper id as well as dataframe)

def add_external_id_to_undownloadable_papers(df: pd.DataFrame, id_list: list[list[str]]) -> pd.DataFrame:
    """
    Add external IDs to a new column in the DataFrame based on matching paper IDs from a list of lists.
    
    :param df: A pandas DataFrame containing paper information, including paperId.
    :param id_list: A list of lists where each sublist contains [paperId, externalId].
    :return: Updated pandas DataFrame with a new column 'externalId_of_undownloadable_paper'.
    """
    # Create a dictionary to map paperId to externalId(s)
    paper_id_to_external_id = {paper_id: external_id for paper_id, external_id in id_list}

    # Initialize the new column with None values
    df['externalId_of_undownloadable_paper'] = None

    # Iterate over the DataFrame rows and update the new column where paper ID matches
    for index, row in df.iterrows():
        paper_id = row['Paper Id of new reference article found']

        # Add the external ID if there's a match in paper_id_to_external_id
        external_id = paper_id_to_external_id.get(paper_id)
        if external_id:
            df.at[index, 'externalId_of_undownloadable_paper'] = external_id

    return df



#add reason for download error

def update_failure_reasons(df: pd.DataFrame, failed_downloads: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Update the DataFrame with a new column 'reason_for_failure' based on the failed downloads list.

    :param df: DataFrame containing paper information.
    :param failed_downloads: List of dictionaries with failed download information, where each dictionary
                              contains 'paper_id' and 'reason' for the failure.
    :return: Updated DataFrame with 'reason_for_failure' column.
    """
    # Convert the list of failed downloads to a dictionary for quick lookup
    failure_dict = {item['paper_id']: item['error'] for item in failed_downloads}

    # Ensure 'reason_for_failure' column exists and is initialized to NaN
    if 'reason_for_failure' not in df.columns:
        df['reason_for_failure'] = pd.NA

    # Update 'reason_for_failure' column based on the failure_dict
    df['reason_for_failure'] = df['Paper Id of new reference article found'].map(failure_dict)

    return df


#Add column of url of all by right able to download papers: use it to potentially pick up papers that did not download without using semantic scholar api

def add_pdf_url_column(df: pd.DataFrame, metadata_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Adds a column to the DataFrame with the URL of the downloadable PDF.
    
    :param df: DataFrame to update.
    :param metadata_list: List of dictionaries containing paper metadata.
    :return: Updated DataFrame with the 'pdf_url' column.
    """
    # Create a dictionary mapping paper IDs to PDF URLs
    pdf_url_dict = {
        paper['paperId']: paper.get('openAccessPdf', {}).get('url', None)
        for paper in metadata_list
        if paper.get('openAccessPdf') and 'url' in paper['openAccessPdf']
    }
    
    # Ensure the 'pdf_url' column exists
    if 'pdf_url' not in df.columns:
        df['pdf_url'] = None

    # Update the DataFrame with PDF URLs
    df['pdf_url'] = df['Paper Id of new reference article found'].map(pdf_url_dict)

    return df


def move_invalid_pdf(pdf_path, invalid_directory):
    """
    Moves the given PDF file to the invalid directory, renaming it if a file with the same name already exists.
    
    Args:
    - pdf_path (str): Path to the PDF file to be moved.
    - invalid_directory (str): Directory to move the invalid PDF to.
    """
    if not os.path.exists(invalid_directory):
        os.makedirs(invalid_directory)

    # Construct the destination path
    destination_path = os.path.join(invalid_directory, os.path.basename(pdf_path))

    # Check if the destination file already exists and handle renaming
    if os.path.exists(destination_path):
        base, extension = os.path.splitext(destination_path)
        i = 1
        while os.path.exists(destination_path):
            destination_path = f"{base}_{i}{extension}"
            i += 1

    try:
        shutil.move(pdf_path, destination_path)
        print(f"Moved invalid PDF to {destination_path}")
    except Exception as e:
        print(f"Failed to move invalid PDF {pdf_path}: {e}")



def update_downloadable_status_invalid(df):
    """
    Update the 'downloadable' column in the DataFrame based on the presence of files in the 'invalid_pdfs' directory.
    
    Args:
    - df (pd.DataFrame): DataFrame containing a column 'PDF File' with file names (excluding .pdf) and a 'downloadable' column.
    
    Returns:
    - pd.DataFrame: Updated DataFrame with 'downloadable' column set to 'no' for files found in the invalid directory.
    """
    invalid_pdfs_dir = 'invalid_pdfs'

    # Check if the invalid_pdfs directory exists
    if not os.path.exists(invalid_pdfs_dir):
        print(f"Directory '{invalid_pdfs_dir}' does not exist. No files marked as downloadable is invalid.")
        return df  # Return the original DataFrame if the directory doesn't exist

    # Get a list of invalid file names (without .pdf extension)
    invalid_files = {os.path.splitext(file)[0] for file in os.listdir(invalid_pdfs_dir)}

    # Update 'downloadable' column based on whether the file is in the invalid directory
    df['downloadable'] = df['Paper Id of new reference article found'].apply(lambda x: 'no' if x in invalid_files else 'yes')

    # Optionally, delete the folder after processing
    delete_folder(invalid_pdfs_dir)

    return df

#clear doc folder


def clear_folder(folder_path):
    """
    Clear all files and subdirectories in the specified folder.
    
    Args:
    - folder_path (str): Path to the folder to be cleared.
    """
    # Check if the folder exists
    if os.path.exists(folder_path):
        # Iterate over all files and directories in the folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                # Remove directory or file
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        print(f"The folder {folder_path} does not exist.")




#get list of paper ids in folder with new ref pdfs
def list_pdf_bases(pdf_folder):
    """
    Lists the base names (without .pdf extension) of all .pdf files in the specified folder.
    
    Parameters:
        pdf_folder (str): Path to the folder containing .pdf files.
        
    Returns:
        list: A list of base names of .pdf files in the folder.
    """
    # List all .pdf files and remove the .pdf extension
    pdf_bases = [os.path.splitext(f)[0] for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    
    return pdf_bases

#replace paper ids with actual names 
def replace_pdf_file_with_title(df, df_found):
    # Create a dictionary mapping 'Paper Id of new reference article found' to 'Title of new reference article found'
    id_to_title = dict(zip(df_found['Paper Id of new reference article found'], df_found['Title of new reference article found']))
    
    # Replace 'PDF file' in df with the corresponding title if the Paper ID matches
    df['PDF File'] = df['PDF File'].map(id_to_title).fillna(df['PDF File'])
    
    return df


def delete_folder(folder_path):
    """
    Deletes the specified folder and all of its contents.
    
    Parameters:
        folder_path (str): The path to the folder to delete.
    """
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
            print(f"Successfully deleted folder: {folder_path}")
        except Exception as e:
            print(f"Error deleting folder {folder_path}: {e}")
    else:
        print(f"Folder does not exist: {folder_path}")

#save text without page number
def save_text_to_file_no_page(text_list, output_file):
    """
    Save extracted text to a .txt file.
    
    Args:
    - text_list (list): List containing text from each page.
    - output_file (str): Path to the output .txt file.
    """
    with open(output_file, 'w', encoding='utf-8') as text_file:
        for page_number, text in enumerate(text_list):
            text_file.write(f"{text}")


#save text with no page number
def full_cycle_no_page(pdf,filename):
    filename=filename+".txt"
    p=extract_text_from_pdf(pdf)
    save_text_to_file_no_page(p,filename)
    filename=read_text_file(filename)

    return filename

#split text according to paragraphs and output as a list

def split_by_paragraph(text):
    return re.split(r'\n\n', text)



# clean text directly as it is

def clean_text(text):
    cleaned_text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
    return cleaned_text


#extract images from pdf

def extract_images_from_pdf(folder_path="main", output_folder="images"):
    # Find the PDF file in the folder
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    
    if not pdf_files:
        print("No PDF file found in the folder.")
        return
    
    # Use the first PDF file found
    pdf_path = os.path.join(folder_path, pdf_files[0])
    print(f"Processing file: {pdf_path}")
    
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Loop through each page to extract images
    for page_num in range(doc.page_count):
        page = doc[page_num]
        images = page.get_images(full=True)  # Get all images on the page

        for img_index, img in enumerate(images):
            xref = img[0]  # Image XREF (identifier within the PDF)
            base_image = doc.extract_image(xref)  # Extract image details
            
            # Extract image bytes and metadata
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]  # Image format (png, jpg, etc.)
            
            # Save the image
            image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
            image_path = os.path.join(output_folder, image_filename)

            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)

            print(f"Saved {image_filename}")

    print("Image extraction complete.")


