from .gpt_rag_asyncio import *
from .call_mongodb import *
import pandas as pd
from dotenv import load_dotenv
import ast
from .embedding import *
import asyncio
from tqdm.asyncio import tqdm_asyncio
from .pdf import *
import string
from tqdm import tqdm
import pandas as pd
import string
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .mongo_client import MongoDBClient


load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoDBClient.get_client()
db = client['data']



async def process_row_async_final(row,text):
    r=[row['Statement'],row['ArticleName']]
    original_statement=row['Statement']
    ans=await call_convert_to_replace(r,text)
    newrow=ast.literal_eval(ans)
    new_row=pd.DataFrame({
        'statement':[original_statement],
        'Statement':[newrow[0]],
        'Reference':[newrow[1]]
    })
    return new_row

async def final_async(df_replacee,text):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    output=[]
    # Process each row asynchronously using the process_row_async function
    # Define a semaphore to limit the number of concurrent tasks (added because VPN cause my tasks to throttle, you can try to remove from this line onwards to)
    semaphore = asyncio.Semaphore(20)  # Adjust the number as needed

    async def process_row_with_semaphore(row,text):
        """Wrapper function to use semaphore for each task."""
        async with semaphore:
            return await process_row_async_final(row,text)
    # Create tasks with semaphore-wrapped function
    tasks = [process_row_with_semaphore(row,text) for _, row in df_replacee.iterrows()]
    #this line then replace with
    #tasks = [process_row_async(row) for _, row in df_replacee.iterrows()]
    #for quicker times (for context, without the vpn a 8 hours task takes 2 hours)
    
    # Use tqdm_asyncio to track progress of async tasks
    for new_row in await tqdm_asyncio.gather(*tasks, desc='Processing rows in parallel'):
        output.append(new_row)
    # Concatenate valid rows
    output_df = pd.concat(output, ignore_index=True) if output else pd.DataFrame()


    return output_df

def finalize(df_replacee, text):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(final_async(df_replacee, text), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, create a new one
        return asyncio.run(final_async(df_replacee, text))


async def process_row_async_edit(row,text):
    r=[row['Edit'],row['ArticleName']]
    statement=row['statement']
    ans=await call_edit_citationer(r,text)
    newrow=ast.literal_eval(ans)
    new_row=pd.DataFrame({
        'statement':[statement],
        'Edit':[newrow[0]],
        'Reference':[newrow[1]]
    })
    return new_row

async def edit_async(df_edit,text):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    output=[]
    # Process each row asynchronously using the process_row_async function
    # Define a semaphore to limit the number of concurrent tasks (added because VPN cause my tasks to throttle, you can try to remove from this line onwards to)
    semaphore = asyncio.Semaphore(20)  # Adjust the number as needed

    async def process_row_with_semaphore(row,text):
        """Wrapper function to use semaphore for each task."""
        async with semaphore:
            return await process_row_async_edit(row,text)
    # Create tasks with semaphore-wrapped function
    tasks = [process_row_with_semaphore(row,text) for _, row in df_edit.iterrows()]
    #this line then replace with
    #tasks = [process_row_async(row) for _, row in df_replacee.iterrows()]
    #for quicker times (for context, without the vpn a 8 hours task takes 2 hours)
    
    # Use tqdm_asyncio to track progress of async tasks
    for new_row in await tqdm_asyncio.gather(*tasks, desc='Processing rows in parallel'):
        output.append(new_row)
    # Concatenate valid rows
    output_df = pd.concat(output, ignore_index=True) if output else pd.DataFrame()


    return output_df
# create citations for edits
def edited(df_edit, text):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(edit_async(df_edit, text), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, create a new one
        return asyncio.run(edit_async(df_edit, text))

async def process_row_async_summary(row,got_authors):
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


async def summarize_score_async(df_replacee,got_authors):
    """Main function to run the parallelized process using asyncio and the async OpenAI client."""
    output=[]
    # Process each row asynchronously using the process_row_async function
    # Define a semaphore to limit the number of concurrent tasks (added because VPN cause my tasks to throttle, you can try to remove from this line onwards to)
    semaphore = asyncio.Semaphore(20)  # Adjust the number as needed

    async def process_row_with_semaphore(row,got_authors=got_authors):
        """Wrapper function to use semaphore for each task."""
        async with semaphore:
            return await process_row_async_summary(row,got_authors=got_authors)
    # Create tasks with semaphore-wrapped function
    tasks = [process_row_with_semaphore(row,got_authors=got_authors) for _, row in df_replacee.iterrows()]
    #this line then replace with
    #tasks = [process_row_async(row) for _, row in df_replacee.iterrows()]
    #for quicker times (for context, without the vpn a 8 hours task takes 2 hours)
    
    # Use tqdm_asyncio to track progress of async tasks
    for new_row in await tqdm_asyncio.gather(*tasks, desc='Processing rows in parallel'):
        output.append(new_row)
    # Concatenate valid rows
    output_df = pd.concat(output, ignore_index=True) if output else pd.DataFrame()


    return output_df

def summarize_score(df_replacee, got_authors=True):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(summarize_score_async(df_replacee, got_authors), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, create a new one
        return asyncio.run(summarize_score_async(df_replacee, got_authors))

    

def switch_sentiment(df_replacee):
    # Apply function to modify Sentiment and Score columns based on Score and Sentiment values
    def update_sentiment_and_score(row):
        if row['score'] in ['Support', 'Oppose']:
            # Switch Sentiment and change Score to 'Relevant'
            new_sentiment = 'support' if row['Sentiment'] == 'oppose' else 'oppose'
            return pd.Series([new_sentiment, 'Relevant'])
        return pd.Series([row['Sentiment'], row['score']])
    
    # Apply the function to each row and update Sentiment and Score columns
    df_replacee[['Sentiment', 'score']] = df_replacee.apply(update_sentiment_and_score, axis=1)
    return df_replacee


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

    test=summarize_score(grouped_chunks)
    test['score'] = test['Summary'].str.extract(r'[\(\[]([^()\[\]]+)[\)\]]$')[0]


    # Remove the last occurrence of text in parentheses from the original 'Summary' column
    test['Summary'] = test['Summary'].str.replace(r'[\(\[]([^()\[\]]+)[\)\]]$', '', regex=True)
    
    #switch sentiment for wrongly classified chunks (rarely occurs)
    test=switch_sentiment(test)
    name=expert+'.xlsx'
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

    test=summarize_score(grouped_chunks,got_authors=False)
    # Extract 'score' from the last pair of brackets at the end of the text
    test['score'] = test['Summary'].str.extract(r'\(([^()\[\]]+)\)$')

    # Remove the last occurrence of parentheses/brackets strictly at the end of the text
    test['Summary'] = test['Summary'].str.replace(r'\(([^()\[\]]+)\)$', '', regex=True).str.strip()
    #switch sentiment for wrongly classified chunks (rarely occurs)
    test=switch_sentiment(test)
    #redo summary for those reference text and reference article that are not unique - means sentiment has changed
    #take out duplicates 
    duplicates = test[test.duplicated(subset=['Reference article name', 'Reference text in main article'], keep=False)]
    unique_df = test.drop_duplicates(subset=['Reference article name', 'Reference text in main article'], keep=False)
    #drop summary then merge the list of sieved chunk and chunk tgt (with the rest being the same)
    df_replacee = duplicates.drop(columns=['Summary', 'Score'], errors='ignore')
    grouped = df_replacee.groupby(['Reference article name', 'Reference text in main article']).agg({
        'Sentiment': 'first',  # Take the first sentiment (or you can modify as needed)
        'Chunk': lambda x: sum(x, []),  # Combine lists of 'Chunk'
        'Sieving by gpt 4o': lambda x: sum(x, []),  # Combine lists of 'Sieving by gpt 4o'
        'Date': 'first',  # Take the first date
    }).reset_index()
    #Redo summary 
    new=summarize_score(grouped,got_authors=False)
    new['score'] = new['Summary'].str.extract(r'[\(\[]([^()\[\]]+)[\)\]]$')[0]


    # Remove the last occurrence of text in parentheses from the original 'Summary' column
    new['Summary'] = new['Summary'].str.replace(r'[\(\[]([^()\[\]]+)[\)\]]$', '', regex=True)
    
    #switch sentiment for wrongly classified chunks (rarely occurs)
    new=switch_sentiment(new)
    #append old unaffected with new affected 
    final=pd.concat([unique_df, new], ignore_index=True)
    records = final.to_dict(orient='records')
    replace_database_collection(uri, db.name, expert, records)
    
#merge selected new data w old data based on inner join statements for comparison
def merge_old_new(expert_new, expert_old, statements, name):
    collection_statements = db[statements]
    documents_statements = list(
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
    df_statement = pd.DataFrame(documents_statements)

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

    # Filter old references with sentiment 'support'
    df_old_support = df_old[df_old['sentiment'] == 'support']

    # Get unique statements from new data
    unique_statements = df_new['statement'].unique()

    # Initialize formatted data list
    formatted_data = []

    for statement in unique_statements:
        # Get new references for the statement
        new_refs = df_new[df_new['statement'] == statement]
        # Get old references for the statement
        old_refs = df_old_support[df_old_support['statement'] == statement].drop_duplicates(subset=['articleName', 'statement'])


        statement_entry = {
            'statement': statement,
            'oldReferences': [],
            'newReferences': []
        }

        # Add new references
        for _, row in new_refs.iterrows():
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
            statement_entry['newReferences'].append(ref_data)

        # Add old references without duplicates
        for _, row in old_refs.iterrows():
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
            # Avoid adding duplicates
            if ref_data not in statement_entry['oldReferences']:
                statement_entry['oldReferences'].append(ref_data)

        formatted_data.append(statement_entry)

    # Replace the collection in the database with the formatted list
    replace_database_collection(uri, db.name, name, formatted_data)

    return formatted_data
#extract citation for matching
async def citation_extract(whole_statement):
    return await call_citation_extractor(whole_statement)

def cite_extract(whole_statement):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(citation_extract(whole_statement), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, use asyncio.run()
        return asyncio.run(citation_extract(whole_statement))

def edit_list(file_content):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(edit_list_async(file_content), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, use asyncio.run()
        return asyncio.run(edit_list_async(file_content))


#extract info to be editted
async def edit_list_async(file_content):
    """Call the async selector to choose the best prompt in the list"""
    return await call_extract_to_edit_async(file_content)

#extract statement citation
async def old_statement_citation_async(text,new_statements):
    return await call_extract_statement_citation(text,new_statements)

#add edits
async def add_edits_async(list,text):
    return await call_add_edits(list,text)


def old_state_cite(text,new_statements):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(old_statement_citation_async(text,new_statements), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, use asyncio.run()
        return asyncio.run(old_statement_citation_async(text,new_statements))

#add edits
def add_edits_cite(list,text):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(add_edits_async(list,text), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, use asyncio.run()
        return asyncio.run(add_edits_async(list,text))
    
#extract reference list and edit it
async def find_reference_async(text):
    """Find reference list"""
    return await call_find_reference_list(text)

async def edit_reference_async(reference_list,list_of_list_references):
    """Edit the reference list"""
    return await call_replace_reference_list(reference_list,list_of_list_references)

#edit citations of statement
async def edit_citation(text,list_statement):
    """Edits citations"""
    return await call_find_to_edit_statement(text,list_statement)

async def process_reference_list_async(text, list_of_list_references):
    """
    Find the reference list in the text and edit it using the provided references,
    edit the text without reference list, 
    then insert the edited reference list at the exact same spot.

    Args:
        text (str): The text to process.
        list_of_list_references (list): List of references to replace the original references.

    Returns:
        str: The updated text with the edited reference list in the original spot.
    """
    # Step 1: Find the reference list in the text
    reference_list = await find_reference_async(text)
    
    # Step 2: Edit the reference list using the provided references
    edited_reference_list = await edit_reference_async(reference_list, list_of_list_references)

    
    # Step 3: Replace the reference list in the exact same spot
    if reference_list in text:
        updated_text = text.replace(reference_list, edited_reference_list)
        print('Reference list replaced')
    else:
        # If reference list is not found, append the new reference list at the end
        updated_text = text.strip() + "\n\n" + edited_reference_list.strip()
        print('Reference list appended at the end (original not found)')
    



    return updated_text

    
def find_edit_references(text,list_of_list_references):
    """Synchronous wrapper function for calling async operations."""
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # Submit the coroutine to the existing loop
        future = asyncio.run_coroutine_threadsafe(process_reference_list_async(text,list_of_list_references), loop)
        return future.result()
    except RuntimeError:
        # No running event loop, use asyncio.run()
        return asyncio.run(process_reference_list_async(text,list_of_list_references))

# Function to clean each reference list in replace db
def clean_references(ref_list):
    if not isinstance(ref_list, list):
        return []
    cleaned_refs = []
    for ref in ref_list:
        # Clean 'date' field
        if 'date' in ref and isinstance(ref['date'], dict):
            if '$numberInt' in ref['date']:
                ref['date'] = int(ref['date']['$numberInt'])
            elif '$numberLong' in ref['date']:
                ref['date'] = int(ref['date']['$numberLong'])
        # Remove 'id' field from the references
        ref.pop('id', None)
        cleaned_refs.append(ref)
    return cleaned_refs


def update_references(df_main, replace_df):
    print(replace_df)
    """
    Updates the main DataFrame by replacing old references, adding new references, and handling edits.

    Parameters:
    - df_main (pd.DataFrame): The main DataFrame containing statements and references.
    - replace_df (pd.DataFrame): The DataFrame containing replacement tasks and edits.

    Returns:
    - pd.DataFrame: The updated main DataFrame with references replaced, added, or updated with edits.
    """
    # Define the normalization function
    def normalize(text):
        if not text:
            return ''
        return ''.join(e for e in text.lower() if e not in string.punctuation).replace(" ", "")
    if replace_df.empty:
        return df_main
    else:
        # Iterate through each unique `_id` in replace_df
        for _id in replace_df['_id'].unique():
            # Filter replace_df for the current `_id`
            ref_data = replace_df[replace_df['_id'] == _id]
            if ref_data.empty:
                print(f"No data found for _id {_id}, skipping.")
                continue
            
            # Extract the statement
            try:
                statement = ref_data['statement'].iloc[0]
            except IndexError:
                print(f"Statement not found for _id {_id}, skipping.")
                continue
            
            # Find the corresponding row in df_main by matching the statement
            main_row = df_main[df_main['statement'] == statement]
            if main_row.empty:
                print(f"Statement '{statement}' not found in df_main for _id {_id}.")
                continue
            
            # Handle old references
            old_ref_series = ref_data[ref_data['referenceType'] == 'Old Reference']['articleName']
            if not old_ref_series.empty:
                old_ref_name = normalize(old_ref_series.iloc[0])
                condition = (df_main['statement'] == statement) & \
                            (df_main['articleName'].apply(normalize) == old_ref_name)
                if not df_main[condition].empty:
                    df_main = df_main[~condition]
                    print(f"Old reference '{old_ref_name}' removed from statement '{statement}'.")
                else:
                    print(f"Old reference '{old_ref_name}' not found for statement '{statement}'.")
            
            # Prepare rows to add
            new_rows = []
            
            # Handle new references
            new_refs = ref_data[ref_data['referenceType'] == 'New Reference']
            for _, new_ref in new_refs.iterrows():
                new_row = {
                    'statement': statement,
                    'authors': new_ref.get('authors', ''),  # Default to '' if no authors
                    'date': new_ref.get('date', ''),        # Default to '' if no date
                    'articleName': new_ref.get('articleName', ''),  # Default to '' if no articleName
                    'edits': new_ref.get('edits', '')       # Default to '' if no edits
                }
                new_rows.append(new_row)
                print(f"Prepared new reference '{new_ref['articleName']}' for statement '{statement}'.")

        # Add edits
        edit_series = ref_data['edits'].dropna()
        for edit in edit_series:
            new_row = {
                'statement': statement,
                'authors': '',  # Default to '' if no authors
                'date': '',     # Default to '' if no date
                'articleName': '',  # Default to '' if no articleName
                'edits': edit
            }
            new_rows.append(new_row)
            print(f"Prepared edit '{edit}' for statement '{statement}'.")

        # Append all new rows at once to df_main
        if new_rows:
            df_main = pd.concat([df_main, pd.DataFrame(new_rows)], ignore_index=True)
    
    return df_main



def preprocess_text(text):
    """
    Preprocesses the text by removing hyphenation at line breaks,
    removing newlines, and condensing multiple spaces into one.
    """
    # Remove hyphenation at line breaks
    text = re.sub(r'-\s+', '', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def merge_statements_and_references(df1, df2):
    """
    Matches statements between two DataFrames, appends content in the `Edits` row to the `Statement` row,
    concatenates the `Reference` lists, and removes rows with matching `statement` where no edits were applied.

    Parameters:
    - df1 (pd.DataFrame): The main DataFrame with `statement`, `Statement`, and `Reference`.
    - df2 (pd.DataFrame): The second DataFrame with `statement`, `Edit`, and `Reference`.

    Returns:
    - pd.DataFrame: Updated DataFrame with merged `Statement` and concatenated `Reference`.
    """
    # Ensure both DataFrames have the necessary columns
    required_columns_df1 = {'statement', 'Statement', 'Reference'}
    required_columns_df2 = {'statement', 'Edit', 'Reference'}

    if not required_columns_df1.issubset(df1.columns):
        raise ValueError(f"df1 must contain the columns: {required_columns_df1}")
    if not required_columns_df2.issubset(df2.columns):
        raise ValueError(f"df2 must contain the columns: {required_columns_df2}")

    # Convert Reference columns to lists if they are not already
    df1['Reference'] = df1['Reference'].apply(lambda x: x if isinstance(x, list) else [])
    df2['Reference'] = df2['Reference'].apply(lambda x: x if isinstance(x, list) else [])

    # Track rows to remove
    rows_to_remove = []

    # Iterate through rows in df2
    for _, row in df2.iterrows():
        matching_rows = df1[df1['statement'] == row['statement']]

        if not matching_rows.empty:
            # Get the index of the matching row
            idx = matching_rows.index[0]

            # Check if an Edit is applied to the Statement
            if row['Edit'] not in df1.at[idx, 'Statement']:
                # Apply the edit
                df1.at[idx, 'Statement'] += f" {row['Edit']}"

                # Concatenate Reference lists
                df1.at[idx, 'Reference'] = list(set(df1.at[idx, 'Reference'] + row['Reference']))

            # Mark the row for removal if no edits were applied
            if not row['Edit']:
                rows_to_remove.append(idx)
        else:
            # If no match, add the row from df2 to df1
            new_row = {
                'statement': row['statement'],
                'Statement': row['statement'] + f" {row['Edit']}",
                'Reference': row['Reference']
            }
            df1 = pd.concat([df1, pd.DataFrame([new_row])], ignore_index=True)

    # Drop the rows marked for removal
    df1 = df1.drop(rows_to_remove).reset_index(drop=True)
    return df1

def edit_paper(df_main,text):
    #get got to :
    #edit reference list
    #edit statement's citations
    #add new statements behind existing statements with their citations

    #Seperate out statements with edits. we will need to add the edits later
    # Separate rows with edits into a new DataFrame
    df_with_edits = df_main[df_main['edits'] != '']
    
    grouped_df_edit = df_with_edits.groupby('statement').apply(
        lambda group: {
            'statement':f"{group['statement'].iloc[0]}",
            'Edit': f"{group['edits'].iloc[0]} ({'; '.join((group['authors'] + ' (' + group['date'].astype(str) + ')').tolist())})",
            'ArticleName': group['articleName'].tolist()
        }
    ).apply(pd.Series).reset_index(drop=True)
    edit_df = grouped_df_edit.rename(
            columns={'statement': 'statement','Edit':'Edit', 'ArticleName': 'ArticleName'}
        )
    edit_df=edited(edit_df,text)
    edit_list=edit_df.values.tolist()

    

    df_without_edits = df_main[df_main['edits'] == '']

    # Group the DataFrame without edits for processing
    grouped_df_with_simple_references = df_without_edits.groupby('statement').apply(
        lambda group: {
            'Statement': f"{group['statement'].iloc[0]} ({'; '.join((group['authors'] + ' (' + group['date'].astype(str) + ')').tolist())})",
            'ArticleNames': group['articleName'].tolist()
        }
    ).apply(pd.Series).reset_index(drop=True)


    # Ensure the resulting dataframe has the correct columns
    final_df = grouped_df_with_simple_references.rename(
        columns={'Statement': 'Statement', 'ArticleNames': 'ArticleName'}
    )
    final_df=finalize(final_df,text)
    if edit_df.empty:
        final=final_df
    else:
        final=merge_statements_and_references(final_df,edit_df)

    #edit reference list to update list, find statements and citations to update:
    list_of_list_reference=final['Reference'].tolist()
    flattened_references = [ref for sublist in list_of_list_reference for ref in sublist]

    # Remove duplicates by converting to a set and back to a list
    unique_references = list(set(flattened_references))
    unique_references.sort()
    list_statements=final['Statement'].tolist()
    new_text=find_edit_references(text,unique_references)
    new=old_state_cite(new_text,list_statements)
    if edit_df.empty:
        n=new
    else:
        n=add_edits_cite(edit_list,text)


    # Full file path
    file_path = f"output_txt/output.txt"
    directory= os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Write the text to the file
    with open(file_path, "w",encoding="utf-8") as file:
        file.write(n)
    print('Answer has been sent as output.txt to output_txt')

    return new




#format based on selection
def formatting():
    #main paper data
    text = read_text_file('extracted.txt')
    result = edit_list(text)
    data=ast.literal_eval(result)
    print('Processing main df')
    # Convert the nested structure to a DataFrame
    df_main = (
        pd.DataFrame(data, columns=["statement", "References"])  # Create DataFrame
        .explode("References")  # Explode References column
        .assign(
            Citation=lambda df_replacee: df_replacee["References"].map(lambda x: x[0] if isinstance(x, list) else None),
            Full_Reference=lambda df_replacee: df_replacee["References"].map(lambda x: x[1] if isinstance(x, list) else None)
        )  # Extract Citation and Full Reference
        .drop(columns=["References"])  # Drop the original References column
    )

    pattern_removecitation = r"\([^)]*\)\s*$"

    df_main['statement']=df_main['statement'].str.replace(pattern_removecitation, "", regex=True)
    pattern_split = r'^(.*?)(?:,?\s+)?(\d{4})$'
    df_main[['authors','date']]=df_main['Citation'].str.extract(pattern_split)

    pattern_title =  r'\)\.\s*(.*?)(?:\. [A-Z]|$)'
    df_main['articleName']=df_main['Full_Reference'].str.extract(pattern_title)
    df_main=df_main.drop(columns=['Citation','Full_Reference'])
    df_main['edits']=''
    print('Processing updates')
    """For edits"""
    edit=db['edit']
    documents_edit=list(list(
        edit.find(
            {},
            {
                '_id':1,
               'statement': 1,
               'edits':1,
               'newReferences': 1,  
            }
        )
    ))
    df_edit=pd.DataFrame(documents_edit)
    if df_edit.empty:
        df_edition=df_edit
    else:
        df_edit['newReferences'] = df_edit['newReferences'].apply(clean_references)
        df_melted_edit = df_edit.melt(
            id_vars=['_id', 'statement','edits'],  
            value_vars=['newReferences'],
            var_name='referenceType',
            value_name='references'
        )
        df_exploded_edit = df_melted_edit.explode('references')
        df_exploded_edit = df_exploded_edit.dropna(subset=['references'])
        # Normalize the references
        references_df_edit = pd.json_normalize(df_exploded_edit['references'])
        df_final_edit = pd.concat([
        df_exploded_edit.drop(columns=['references']).reset_index(drop=True),
                references_df_edit.reset_index(drop=True)
            ], axis=1)
        df_final_edit['referenceType'] = df_final_edit['referenceType'].map({
            'newReferences': 'New Reference'
        })
        df_edition = df_final_edit[['_id', 'statement','edits', 'referenceType', 'articleName', 'authors', 'date']]
        print(df_edition)
    
    


    """For addition"""
    addition=db['addition']
    documents_add=list(list(
        addition.find(
                {}, 
                {
                    '_id': 1,             
                    'statement': 1,       
                    'newReferences': 1,   
                }
            )
        )
    )
    df_add = pd.DataFrame(documents_add)
    if df_add.empty:
        df_addition=df_add
    else:
        df_add['newReferences'] = df_add['newReferences'].apply(clean_references)
        df_melted_add = df_add.melt(
            id_vars=['_id', 'statement'],  # Include '_id' (statement id)
            value_vars=['newReferences'],
            var_name='referenceType',
            value_name='references'
        )
        df_exploded_add = df_melted_add.explode('references')
        df_exploded_add = df_exploded_add.dropna(subset=['references'])
        # Normalize the references
        references_df_add = pd.json_normalize(df_exploded_add['references'])
        df_final_add = pd.concat([
        df_exploded_add.drop(columns=['references']).reset_index(drop=True),
                references_df_add.reset_index(drop=True)
            ], axis=1)
        df_final_add['referenceType'] = df_final_add['referenceType'].map({
            'oldReferences': 'Old Reference',
            'newReferences': 'New Reference'
        })
        df_addition = df_final_add[['_id', 'statement', 'referenceType', 'articleName', 'authors', 'date']]
        df_addition['edits']=''
        print(df_addition)

    """
    For replacement
    """
    replace = db['replace']
    documents_new = list(
        replace.find(
            {}, 
            {
                '_id': 1,             
                'statement': 1,       
                'oldReferences': 1,   
                'newReferences': 1,   
            }
        )
    )
    df_replacee = pd.DataFrame(documents_new)
    if df_replacee.empty:
        df_replace=df_replacee
    else:
        df_replacee['oldReferences'] = df_replacee['oldReferences'].apply(clean_references)
        df_replacee['newReferences'] = df_replacee['newReferences'].apply(clean_references)
        df_melted = df_replacee.melt(
            id_vars=['_id', 'statement'],  # Include '_id' (statement id)
            value_vars=['oldReferences', 'newReferences'],
            var_name='referenceType',
            value_name='references'
        )
        df_exploded = df_melted.explode('references')
        df_exploded = df_exploded.dropna(subset=['references'])

        # Normalize the references
        references_df = pd.json_normalize(df_exploded['references'])
        df_final = pd.concat([
        df_exploded.drop(columns=['references']).reset_index(drop=True),
                references_df.reset_index(drop=True)
            ], axis=1)



        # Rename 'referenceType' values for readability
        df_final['referenceType'] = df_final['referenceType'].map({
            'oldReferences': 'Old Reference',
            'newReferences': 'New Reference'
        })

        # Rearrange the columns
        df_replace = df_final[['_id', 'statement', 'referenceType', 'articleName', 'authors', 'date']]
        df_replace['edits']=''
        print(df_replace)
        #change the old ref w new ref 
        # Perform the replacement and track changes
    if df_replace.empty and df_addition.empty and df_edition.empty:
        updated_df_main = df_main
        print('replace, addition, and edition dfs are empty')
        edit_paper(updated_df_main,text)
        records = updated_df_main.to_dict(orient='records')
        replace_database_collection(uri, db.name, 'to_update', records)
        return
    elif df_replace.empty and df_addition.empty:
        df_changes = df_edition
        print('replace and addition dfs are empty')
    elif df_replace.empty and df_edition.empty:
        df_changes = df_addition
        print('replace and edition dfs are empty')
    elif df_addition.empty and df_edition.empty:
        df_changes = df_replace
        print('addition and edition dfs are empty')
    elif df_replace.empty:
        df_changes = pd.concat([df_addition, df_edition], ignore_index=True)
        print('replace df empty')
    elif df_addition.empty:
        df_changes = pd.concat([df_replace, df_edition], ignore_index=True)
        print('addition df empty')
    elif df_edition.empty:
        df_changes = pd.concat([df_replace, df_addition], ignore_index=True)
        print('edition df empty')
    else:
        df_changes = pd.concat([df_replace, df_addition, df_edition], ignore_index=True)
        print('all dfs have data')
    send_excel(df_changes,'RAG','changes.xlsx')

    updated_df_main = update_references(df_main, df_changes)

    #Perform final edited table to insert for regex matching
    edit_paper(updated_df_main,text)
    records = updated_df_main.to_dict(orient='records')
    replace_database_collection(uri, db.name, 'to_update', records)
   
