import os
from openpyxl import Workbook
import unicodedata

# Your existing list of file names
d = [
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

# Assuming your function `full_cycle` processes the PDF and writes to text files
# and you have them stored in the 'doc' directory with names like '0.txt', '1.txt', etc.
Doc = [f"{i}.txt" for i in range(len(d))]

# Read the processed content from each text file and store in a list
processed_texts = []
for filename in Doc:
    input_path = os.path.join('doc', filename)
    with open(input_path, 'r', encoding='utf-8') as f:
        processed_text = f.read()
        # Clean text (remove non-printable characters)
        cleaned_text = ''.join(char for char in processed_text if unicodedata.category(char)[0] != 'C')
        processed_texts.append(cleaned_text)

# Create a new Workbook and select the active worksheet
workbook = Workbook()
sheet = workbook.active

# Add headers (optional)
sheet['A1'] = 'PDF File'
sheet['B1'] = 'Text Content'

# Populate data into worksheet
for index, pdf_name in enumerate(d, start=2):  # Start from row 2 for data
    sheet[f'A{index}'] = pdf_name
    sheet[f'B{index}'] = processed_texts[index - 2]  # Index adjusted for zero-based list

# Save workbook to a file
excel_filename = 'processed_documents.xlsx'
workbook.save(excel_filename)

print(f'Data has been written to {excel_filename}')
