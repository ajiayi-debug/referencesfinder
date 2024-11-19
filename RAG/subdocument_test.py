from .pdf import *
from .gpt_rag import *
from .semantic_chunking import *
import pandas as pd
from .embedding import *
import ast

text=full_cycle('text/heyman.pdf', 'heyman_test')
text=clean_text(text)
split_page=chunk_text_by_page(text)


# data = {'PDF File': processed_name, 'Text Content': processed_texts}
# df = pd.DataFrame(data)

summary=[]
for sp in split_page:
    summary.append(summarise_subdocument(sp))

data={'Subdocument by page': split_page, 'Summary of Subdocument': summary}

df=pd.DataFrame(data)

df['Text Chunks'] = df['Subdocument by page'].apply(semantic_chunk)
df = df.explode('Text Chunks')

print(df)
split_df = splitting(df, 'Text Chunks')
token_df = tokenize(split_df, 'Text Chunks')
chunki = chunking(token_df, 'Text Chunks', 8190)

emb=embed(chunki)
final_ans='subdocument_chunking.xlsx'
send_excel(emb,'RAG', final_ans)

ref="A proportion of the world’s population is able to tolerate lactose as they have a genetic variation that ensures they continue to produce sufficient quantities of the enzyme lactase after childhood."

#emb['gpt4o retrieval']=emb['Summary of Subdocument'].apply(lambda x: locate_subdoc(x, ref))

#send_excel(emb, 'RAG', 'subdocument_chunking_locate.xlsx')

test=emb['Summary of Subdocument'].unique().tolist()

ans=[]
for t in test:
    ans.append(locate_subdoc(t,ref))

summary_ans_ref = [[x, y,ref] for x, y in zip(test, ans)]

list_df=pd.DataFrame(summary_ans_ref, columns=['Summary','Contains reference','Reference'])

merged_df = pd.merge(emb, list_df, left_on='Summary of Subdocument', right_on='Summary', how='left')

final_df = merged_df.drop(columns=['Summary'])

final_df['Contains reference'] = final_df['Contains reference'].str.lower()

focus_df = final_df[final_df['Contains reference'] == 'yes']
dfs = []
similiar=retrieve_similar_text_threshold_text_only(focus_df, ref, 10, 0.5)
print(similiar)
print(similiar==True)

send_excel(final_df, 'RAG', 'subdocument_yes_no.xlsx')

send_excel(focus_df, 'RAG', 'subdocument_yes.xlsx')

send_excel(similiar, 'RAG', 'subdocument_output.xlsx')
