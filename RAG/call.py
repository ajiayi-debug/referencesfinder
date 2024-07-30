from pdf import *
from gpt_rag import *
from embedding import *
import ast
import pandas as pd
from dotenv import *
pdf_to_check=os.getenv("PDF")

def main():
    output_directory = 'RAG'
    df=read_file("processed.xlsx",output_directory)
    text=full_cycle(pdf_to_check,filename="extracted")
    output=get_references(text)
    codable=ast.literal_eval(output)

    # turns out gpt 4o is better than cosine similiarity as the text chunks are still too long for accurate representation of vectors, so cosine similiarity is off. Still, we can keep the embbedded database for future references!
    
    dfs = []
    for code in codable:
        pdf = retrieve_pdf(df, code)
        best = focus_on_best(pdf)
        getans = similiar_ref(code[0], best)
        
        # Create a DataFrame for the current row and specify an index
        row = pd.DataFrame({'reference article name': [code[1]], 'Reference text in main article': [code[0]], 'Reference text in reference article': [getans]})
        
        dfs.append(row)
    
    # Concatenate all row DataFrames into one
    output_df = pd.concat(dfs, ignore_index=True)
    
    # Specify the file name and path
    final_ans = 'find_ref_non_embed.xlsx'
    send_excel(output_df,output_directory,final_ans)
    




if __name__ == "__main__":
    main()