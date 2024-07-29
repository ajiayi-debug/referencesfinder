from pdf import *
from gpt_rag import *
from embedding import *
import ast
import pandas as pd


def main():
    output_directory = 'RAG'
    df=read_file("processed.xlsx",output_directory)
    embed_filename="embedded.xlsx"
    content='Text Content'
    split_df=splitting(df,content)
    token_df=tokenize(split_df,content)
    chunki=chunking(token_df,content,8190)
    emb=embed(chunki)
    send_excel(emb, output_directory, embed_filename)
    text=full_cycle("FC-Institute-Publication-on-Lactose-intolerance_2022.pdf",filename="extracted")
    output=get_references(text)
    codable=ast.literal_eval(output)

    
    
    dfs = []
    for code in codable:
        pdf = retrieve_pdf(emb, code)
        similiar = retrieve_similiar_text(pdf, code)  # Returns rows of refs that have semantically similar meaning to text of main pdf
        best = focus_on_best(similiar)
        getans = similiar_ref(code[0], best)
        
        # Create a DataFrame for the current row and specify an index
        row = pd.DataFrame({'reference article name': [code[1]], 'Reference text in main article': [code[0]], 'Reference text in reference article': [getans]})
        
        dfs.append(row)
    
    # Concatenate all row DataFrames into one
    output_df = pd.concat(dfs, ignore_index=True)
    
    # Specify the file name and path
    final_ans = 'find_ref.xlsx'
    send_excel(output_df,output_directory,final_ans)
    




if __name__ == "__main__":
    main()