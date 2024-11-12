from gpt_rag_asyncio import *
from call_mongodb import *
import pandas as pd
from dotenv import load_dotenv
import ast
from embedding import *
import asyncio
from tqdm.asyncio import tqdm_asyncio
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
db = client['data']

loop = asyncio.get_event_loop()


async def process_row_async(row):
    """Async function to process each row in the DataFrame using the async Azure OpenAI call."""
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
        'authors':[authors]
    })
    return new_row


async def summarize_score_async(df):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    output=[]
    # Process each row asynchronously using the process_row_async function
    # Define a semaphore to limit the number of concurrent tasks (added because VPN cause my tasks to throttle, you can try to remove from this line onwards to)
    semaphore = asyncio.Semaphore(20)  # Adjust the number as needed

    async def process_row_with_semaphore(row):
        """Wrapper function to use semaphore for each task."""
        async with semaphore:
            return await process_row_async(row)
    # Create tasks with semaphore-wrapped function
    tasks = [process_row_with_semaphore(row) for _, row in df.iterrows()]
    #this line then replace with
    #tasks = [process_row_async(row) for _, row in df.iterrows()]
    #for quicker times (for context, without the vpn a 8 hours task takes 2 hours)
    
    # Use tqdm_asyncio to track progress of async tasks
    for new_row in await tqdm_asyncio.gather(*tasks, desc='Processing rows in parallel'):
        output.append(new_row)
    # Concatenate valid rows
    output_df = pd.concat(output, ignore_index=True) if output else pd.DataFrame()


    return output_df

def summarize_score(df):
    """Synchronous wrapper function for calling async operations."""
    global loop

    # Check if the event loop is already running
    if loop.is_running():
        # Use asyncio.run_coroutine_threadsafe to submit async work to the existing loop
        return asyncio.run_coroutine_threadsafe(summarize_score_async(df), loop).result()
    else:
        # Otherwise, create and run a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(summarize_score_async(df))

#function to split data according to reference article name, reference text in main article and sentiment
#then, we take all sieving by gpt 4o to summarize according t how much support/oppose reference text in main article
#We also need to score how much paper supports/oppose statement as an overall of all top sieved chunks. 
#include authors for citation
def make_pretty_for_expert(top_5,new_ref_collection ):
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
        ['Sentiment', 'Reference article name', 'Reference text in main article', 'authors']
    ).agg({
        'Chunk': list,
        'Sieving by gpt 4o': list
    }).reset_index()

    # No need to apply ast.literal_eval on 'Chunk' or 'Sieving by gpt 4o' since they are already text
    print(grouped_chunks.columns)
    test=summarize_score(grouped_chunks)
    send_excel(test,'RAG','test.xlsx')
    
make_pretty_for_expert('top_5','new_ref_found_Agentic')