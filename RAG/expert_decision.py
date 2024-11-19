from .gpt_rag_asyncio import *
from .call_mongodb import *
import pandas as pd
from dotenv import load_dotenv
import ast
from .embedding import *
import asyncio
from tqdm.asyncio import tqdm_asyncio
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']

loop = asyncio.get_event_loop()


async def process_row_async(row,got_authors):
    #for new top 5 where authors are added
    if got_authors:
        list_of_sieved_chunks = row['Sieving by gpt 4o']
        if isinstance(list_of_sieved_chunks, str):
            list_of_sieved_chunks = ast.literal_eval(list_of_sieved_chunks)
        statement=row['Reference text in main article']
        sentiment = str(row['Sentiment']).strip()
        name=row['Reference article name']
        authors=row['authors']
        chunk=row['Chunk']
        if isinstance(chunk, str):
            chunk = ast.literal_eval(chunk)
        date=row.loc['Date']
        await asyncio.sleep(10)
        # Use the async wrapper to call the GPT service with retry logic
        #ans = await call_summarizer_scorer_async(list_of_sieved_chunks,statement,sentiment)
        ans = await call_summarizer_scorer_async(chunk,statement,sentiment)
        
        new_row = pd.DataFrame({
            'Sentiment':[sentiment],
            'Sieving by gpt 4o': [list_of_sieved_chunks],
            'Chunk':[chunk],
            'Reference article name': [name],
            'Reference text in main article': [statement],
            'Summary':[ans],
            'authors':[authors],
            'Date':[date]
        })
    #for old top 5 where no authors added
    else:
        """Async function to process each row in the DataFrame using the async Azure OpenAI call."""
        list_of_sieved_chunks = row['Sieving by gpt 4o']
        if isinstance(list_of_sieved_chunks, str):
            list_of_sieved_chunks = ast.literal_eval(list_of_sieved_chunks)
        statement=row['Reference text in main article']
        sentiment = str(row['Sentiment']).strip()
        name=row['Reference article name']
        chunk=row['Chunk']
        if isinstance(chunk, str):
            chunk = ast.literal_eval(chunk)
        date=row.loc['Date']
        await asyncio.sleep(10)
        # Use the async wrapper to call the GPT service with retry logic
        #ans = await call_summarizer_scorer_async(list_of_sieved_chunks,statement,sentiment)
        ans = await call_summarizer_scorer_async(chunk,statement,sentiment)
        
        new_row = pd.DataFrame({
            'Sentiment':[sentiment],
            'Sieving by gpt 4o': [list_of_sieved_chunks],
            'Chunk':[chunk],
            'Reference article name': [name],
            'Reference text in main article': [statement],
            'Summary':[ans],
            'Date':[date]
        })
    return new_row


async def summarize_score_async(df,got_authors):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    output=[]
    # Process each row asynchronously using the process_row_async function
    # Define a semaphore to limit the number of concurrent tasks (added because VPN cause my tasks to throttle, you can try to remove from this line onwards to)
    semaphore = asyncio.Semaphore(20)  # Adjust the number as needed

    async def process_row_with_semaphore(row,got_authors=got_authors):
        """Wrapper function to use semaphore for each task."""
        async with semaphore:
            return await process_row_async(row,got_authors=got_authors)
    # Create tasks with semaphore-wrapped function
    tasks = [process_row_with_semaphore(row,got_authors=got_authors) for _, row in df.iterrows()]
    #this line then replace with
    #tasks = [process_row_async(row) for _, row in df.iterrows()]
    #for quicker times (for context, without the vpn a 8 hours task takes 2 hours)
    
    # Use tqdm_asyncio to track progress of async tasks
    for new_row in await tqdm_asyncio.gather(*tasks, desc='Processing rows in parallel'):
        output.append(new_row)
    # Concatenate valid rows
    output_df = pd.concat(output, ignore_index=True) if output else pd.DataFrame()


    return output_df

def summarize_score(df, got_authors=True):
    """Synchronous wrapper function for calling async operations."""
    global loop

    # Check if the event loop is already running
    if loop.is_running():
        # Use asyncio.run_coroutine_threadsafe to submit async work to the existing loop
        return asyncio.run_coroutine_threadsafe(summarize_score_async(df,got_authors=got_authors), loop).result()
    else:
        # Otherwise, create and run a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(summarize_score_async(df,got_authors=got_authors))
    

def switch_sentiment(df):
    # Apply function to modify Sentiment and Score columns based on Score and Sentiment values
    def update_sentiment_and_score(row):
        if row['score'] in ['Support', 'Oppose']:
            # Switch Sentiment and change Score to 'Relevant'
            new_sentiment = 'support' if row['Sentiment'] == 'oppose' else 'oppose'
            return pd.Series([new_sentiment, 'Relevant'])
        return pd.Series([row['Sentiment'], row['score']])
    
    # Apply the function to each row and update Sentiment and Score columns
    df[['Sentiment', 'score']] = df.apply(update_sentiment_and_score, axis=1)
    return df


#function to split data according to reference article name, reference text in main article and sentiment
#then, we take all sieving by gpt 4o to summarize according t how much support/oppose reference text in main article
#We also need to score how much paper supports/oppose statement as an overall of all top sieved chunks. 
#include authors for citation
def make_pretty_for_expert(top_5,new_ref_collection,expert):
    collection_top5 = db[top_5]
    documents = list(
        collection_top5.find(
            {}, 
            {
                '_id': 1,
                'Sentiment':1,
                'Confidence Score':1,
                'Sieving by gpt 4o': 1,
                'Reference article name': 1,
                'Reference text in main article': 1,
                'Chunk': 1,
                'Date': 1
            }
        )
    )
    df_top5=pd.DataFrame(documents)

    collection_metadata=db[new_ref_collection]
    documents1=list(
        collection_metadata.find(
            {},
            {
                '_id': 1,
                'Title of original reference article':1,
                'Text in main article referencing reference article':1,
                'Year reference article released':1,
                'Keywords for graph paper search':1,
                'Paper Id of new reference article found':1,
                'Title of new reference article found':1,
                'Year new reference article found published':1,
                'authors':1
            }
        )
    )

    df_metadata=pd.DataFrame(documents1)
    
    df_metadata['authors'] = df_metadata['authors'].apply(
        lambda authors_list: [author['name'] for author in authors_list] if isinstance(authors_list, list) else []
    )
    # Extract author names for each row and replace the existing 'authors' column
    title_to_authors = df_metadata.set_index('Title of new reference article found')['authors'].to_dict()

    #Add authors to df_top5 based on matching titles
    df_top5['authors'] = df_top5['Reference article name'].apply(
        lambda title: ', '.join(title_to_authors[title]) if title in title_to_authors else ''
    )
    grouped_chunks = df_top5.groupby(
        ['Sentiment', 'Reference article name', 'Reference text in main article', 'authors','Date']
    ).agg({
        'Chunk': list,
        'Sieving by gpt 4o': list
    }).reset_index()

    # No need to apply ast.literal_eval on 'Chunk' or 'Sieving by gpt 4o' since they are already text
    print(grouped_chunks.columns)

    test=summarize_score(grouped_chunks)
    test['score'] = test['Summary'].str.extract(r'[\(\[]([^()\[\]]+)[\)\]]$')[0]


    # Remove the last occurrence of text in parentheses from the original 'Summary' column
    test['Summary'] = test['Summary'].str.replace(r'[\(\[]([^()\[\]]+)[\)\]]$', '', regex=True)
    
    #switch sentiment for wrongly classified chunks (rarely occurs)
    test=switch_sentiment(test)
    name=expert+'.xlsx'
    send_excel(test,'RAG',name)
    records = test.to_dict(orient='records')
    replace_database_collection(uri, db.name, expert, records)
    



#To make summary of original references in order to compare and see if new references found should supplement or replace the old references based on summary of retrieved content
def make_summary_for_comparison(top_5,expert):
    collection_top5 = db[top_5]
    documents = list(
        collection_top5.find(
            {}, 
            {
                '_id': 1,
                'Sentiment':1,
                'Confidence Score':1,
                'Sieving by gpt 4o': 1,
                'Reference article name': 1,
                'Reference text in main article': 1,
                'Chunk': 1,
                'Date': 1
            }
        )
    )
    df_top5=pd.DataFrame(documents)
    grouped_chunks = df_top5.groupby(
        ['Sentiment', 'Reference article name', 'Reference text in main article','Date']
    ).agg({
        'Chunk': list,
        'Sieving by gpt 4o': list
    }).reset_index()

    # No need to apply ast.literal_eval on 'Chunk' or 'Sieving by gpt 4o' since they are already text
    print(grouped_chunks.columns)

    test=summarize_score(grouped_chunks,got_authors=False)
    # Extract 'score' from the last pair of brackets at the end of the text
    test['score'] = test['Summary'].str.extract(r'\(([^()\[\]]+)\)$')

    # Remove the last occurrence of parentheses/brackets strictly at the end of the text
    test['Summary'] = test['Summary'].str.replace(r'\(([^()\[\]]+)\)$', '', regex=True).str.strip()
    #switch sentiment for wrongly classified chunks (rarely occurs)
    test=switch_sentiment(test)
    name=expert+'.xlsx'
    send_excel(test,'RAG',name)
    records = test.to_dict(orient='records')
    replace_database_collection(uri, db.name, expert, records)
    
#merge selected new data w old data based on inner join statements for comparison
def merge_old_new(expert_new, expert_old,statements,name):
    collection_statements=db[statements]
    documents_statements=list(
        collection_statements.find(
            {}, 
            {
                'Reference article name': 1, 
                'Reference text in main article': 1, 
                'Date': 1,
                'Name of authors': 1
            }
        )
    )
    df_statement=pd.DataFrame(documents_statements)
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
    df_old['authors'] = df_old.apply(
        lambda row: ", ".join(
            df_statement.loc[
                (df_statement['Reference text in main article'] == row['statement']) &
                (df_statement['Reference article name'] == row['articleName']), 
                'Name of authors'
            ].tolist()
        ),
        axis=1
    )

    # Create a new DataFrame to store matches
    matched_df = pd.DataFrame(columns=df_new.columns)

    for _, new_row in df_new.iterrows():
        matching_old_rows = df_old[(df_old['statement'] == new_row['statement']) & (df_old['sentiment'] == 'support')]
        if not matching_old_rows.empty:
            # Append the new row
            matched_df = matched_df._append(new_row, ignore_index=True)
            # Append all matching old rows where sentiment is 'support'
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