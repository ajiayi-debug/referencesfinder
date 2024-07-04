from gptapi import *
from pdftotext import *

perfect_prompt="What are the references in the text? List out the full references for me. Then, list out the full texts that references these references according to page number."
user_input="You are in charge of updating PDFs for the company. In the following text, what are the references in the text? List out the full references. Then, list out the full texts that references these references according to page number. Make sure to state any mistakes in the referencing such as duplicate referencing or unused referencing."
PDF="FC-Institute-Publication-on-Lactose-intolerance_2022.pdf"
filename="extracted"

# text=full_cycle(PDF,filename)

# output=request(text)

# print(output)

def main(PDF,filename):
    text=full_cycle(PDF,filename)
    output=request(text)
    print(output)

if __name__=="__main__":
    main(PDF,filename)
    