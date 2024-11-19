from .call_mongodb import *
import pandas as pd
from dotenv import load_dotenv
import os
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']

#merge selected new data w old data based on inner join statements for comparison
def merge_old_new(expert_new, expert_old,name):
    # Fetch new data
    collection_new = db[expert_new]
    documents_new = list(
        collection_new.find(
            {}, 
            {
                'sentiment': 1,
                'sievingByGPT4o': 1,
                'chunk': 1,
                'articleName': 1,
                'statement': 1,
                'summary': 1,
                'authors': 1,
                'date': 1,
                'rating': 1
            }
        )
    )
    df_new = pd.DataFrame(documents_new)
    df_new['state'] = 'new'  # Add state column for new data

    # Fetch old data
    collection_old = db[expert_old]
    documents_old = list(
        collection_old.find(
            {}, 
            {
                'Sentiment': 1,
                'Sieving by gpt 4o': 1,
                'Chunk': 1,
                'Reference article name': 1,
                'Reference text in main article': 1,
                'Summary': 1,
                'Date': 1,
                'score': 1
            }
        )
    )
    df_old = pd.DataFrame(documents_old)
    df_old = df_old.rename(columns={
        'Sentiment': 'sentiment',
        'Sieving by gpt 4o': 'sievingByGPT4o',
        'Chunk': 'chunk',
        'Reference article name': 'articleName',
        'Summary': 'summary',
        'Date': 'date',
        'score': 'rating',
        'Reference text in main article': 'statement'
    })
    df_old['state'] = 'old'
    df_old['authors'] = ''  # Add authors column for old data

    # Create a new DataFrame to store matches
    matched_df = pd.DataFrame(columns=df_new.columns)

    for _, new_row in df_new.iterrows():
        matching_old_rows = df_old[df_old['statement'] == new_row['statement']]
        if not matching_old_rows.empty:
            # Append the new row
            matched_df = matched_df._append(new_row, ignore_index=True)
            # Append all matching old rows
            matched_df = matched_df._append(matching_old_rows, ignore_index=True)

    # Format the data for the frontend
    formatted_data = {}
    for _, row in matched_df.iterrows():
        statement = row['statement']
        ref_data = {
            "id": row["_id"],
            "articleName": row["articleName"],
            "date": row["date"],
            "sieved": row.get("sievingByGPT4o", []),
            "chunk": row.get("chunk", []),
            "summary": row["summary"],
            "authors": row.get("authors"),
            "sentiment": row.get("sentiment")
        }

        # Initialize statement group if it doesn't exist
        if statement not in formatted_data:
            formatted_data[statement] = {
                "statement": statement,
                "oldReferences": [],
                "newReferences": []
            }

        # Append to the appropriate list
        if row["state"] == "old":
            formatted_data[statement]["oldReferences"].append(ref_data)
        elif row["state"] == "new":
            formatted_data[statement]["newReferences"].append(ref_data)

    # Convert to list of dictionaries for JSON compatibility
    formatted_list = list(formatted_data.values())
    replace_database_collection(uri, db.name, name, formatted_list)

    return formatted_list
