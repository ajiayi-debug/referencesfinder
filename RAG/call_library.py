from pdf import *
from gpt_rag import *
from embedding import *
import ast

def main():
    output_directory = 'RAG'
    df=read_file("processed.xlsx",output_directory)
    embed_filename="embedded.xlsx"
    content='Text Content'
    split_df=splitting(df,content)
    token_df=tokenize(split_df,content)
    chunki=chunking(token_df,content,8190)
    emb=embed(chunki)
    send_embed_excel(emb, output_directory, embed_filename)
    text=full_cycle("FC-Institute-Publication-on-Lactose-intolerance_2022.pdf",filename="extracted")
    output=get_references(text)
    codable=ast.literal_eval(output)

    for code in codable:
        print(code)
        pdf=retrieve_pdf(emb,code)
        similiar=retrieve_similiar_text(pdf,code) #returns rowsss of refs
        print(similiar)
        # rag=similiar_ref()
    




if __name__ == "__main__":
    main()