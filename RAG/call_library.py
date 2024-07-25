from pdf import *
from gpt_rag import *
from embedding import *
import ast

def main():
    text=full_cycle("FC-Institute-Publication-on-Lactose-intolerance_2022.pdf",filename="extracted")
    output=get_references(text)
    codable=ast.literal_eval(output)
    df=read_file("embedded.xlsx","RAG")
    for code in codable:
        pdf=retrieve_pdf(df,code)
        similiar=retrieve_similiar_text(pdf,code)
        #print(similiar)
        #rag=similiar_ref()
    




if __name__ == "__main__":
    main()