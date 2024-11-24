from .gpt_rag_asyncio import *
from .call_mongodb import *
from dotenv import load_dotenv
import asyncio
from .mongo_client import MongoDBClient
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoDBClient.get_client()
db = client['data']

async def generate_improved_prompt(old_prompt):
    """Call the async rewriter to generate a better prompt."""
    return await call_rewritter_async(old_prompt)

async def choose_best_prompt(list_of_prompts):
    """Call the async selector to choose the best prompt in the list"""
    return await call_selector_async(list_of_prompts)

#chooses best prompt according to history else generates a new prompt
def evaluator(old_prompt,collection):
    list_of_prompts=get_effective_prompts(uri,db.name,collection)
    #try to select from list of prompts that are effective first
    if list_of_prompts:  # Checks if list is not empty
        list_of_prompts = str(list_of_prompts)
        try:
            new_prompt = asyncio.run(choose_best_prompt(list_of_prompts))
        except Exception as e:
            print(f"Error in async call_selector_async: {e}")
            new_prompt = old_prompt  # Fall back to the old prompt
    #generate prompts not in list of effective prompts (may generate a repeat prompt but not in list of effective)
    else:
        try:
            new_prompt = asyncio.run(generate_improved_prompt(old_prompt))
        except Exception as e:
            print(f"Error in async generate_improved_prompt: {e}")
            new_prompt = old_prompt  # Fall back to the old prompt
    return new_prompt

def effectiveness_state(missing_ref_df_initial, missing_ref_df_new, prompt,collection):
    """
    Updates the effectiveness state of a prompt based on the change in missing references.

    Args:
        missing_ref_df_initial (DataFrame): Initial dataframe of missing references.
        missing_ref_df_new (DataFrame): New dataframe of missing references after using the prompt.
        prompt (str): The prompt being evaluated.
    """
    if len(missing_ref_df_new) < len(missing_ref_df_initial):
        # Prompt was effective, mark it as effective
        change_prompt_state_or_add(uri, db.name, collection, prompt, effective='Y')
    else:
        # Prompt was not effective, mark it as not effective
        change_prompt_state_or_add(uri, db.name, collection, prompt, effective='N')