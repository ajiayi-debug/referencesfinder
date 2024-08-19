from pdf import *
from gpt_rag import *
from embedding import *
import ast
import pandas as pd
from dotenv import *
from pymongo import MongoClient
from call_mongodb import *
from tqdm import tqdm



def main():
    output_directory = 'RAG'
    df5=read_file("find_ref_new_embed_pruned_top5.xlsx",output_directory)
    df10=read_file("find_ref_new_embed_pruned_top10.xlsx",output_directory)
    tqdm.pandas()

    df5['Cleaned Reference'] = df5['Reference identified by gpt4o in chunk'].apply(clean_away_nonsemantic)
    df5 = df5[df5['Cleaned Reference'] != '*']
    df5 = df5.drop(columns=['Cleaned Reference'])
    df5 = df5[df5['Reference text in main article'] != df5['Reference identified by gpt4o in chunk']]
    
    df10['Cleaned Reference'] = df10['Reference identified by gpt4o in chunk'].apply(clean_away_nonsemantic)
    df10 = df10[df10['Cleaned Reference'] != '*']
    df10 = df10.drop(columns=['Cleaned Reference'])
    df10 = df10[df10['Reference text in main article'] != df10['Reference identified by gpt4o in chunk']]

    
    # Specify the file name and path
    final_ans_5 = 'find_ref_new_embed_pruned_top5_cleaned.xlsx'
    send_excel(df5,output_directory,final_ans_5)
    final_ans_10 = 'find_ref_new_embed_pruned_top10_cleaned.xlsx'
    send_excel(df10,output_directory,final_ans_10)
    




if __name__ == "__main__":
    main()