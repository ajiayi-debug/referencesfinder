import fitz  # PyMuPDF

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
    p=extract_text_from_pdf(pdf)
    d=save_text_to_file(p,filename)
    filename=read_text_file(filename)

    return filename




