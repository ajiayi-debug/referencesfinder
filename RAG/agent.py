from .gpt_rag_asyncio import *
from .call_mongodb import *
from dotenv import load_dotenv
import asyncio
from .mongo_client import MongoDBClient
load_dotenv()
uri = os.getenv("uri_mongo")
client = MongoDBClient.get_client()
db = client['data']

"""For agentic search system"""
#generates a better prompt than old prompt for keyword generator
async def generate_improved_prompt(old_prompt):
    """Call the async rewriter to generate a better prompt."""
    return await call_rewritter_async(old_prompt)

#choose the best prompt out of the list of effective prompts for agentic search
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


"""For agentic initial check system"""
#statement extractor
async def get_statements_async(text,prompt=None):
    ans = await call_get_ref_async(text,prompt)
    return ans

#statement extractor checker
async def check_statement_output(output,text):
    ans = await call_check_statement_extraction(output,text)
    return ans

#output editor for mistales
async def edit_mistakes_in_output(mistakes):
    ans = await call_edit_mistakes_async(mistakes)
    return ans

#statement extractor checker
async def check_only_statement_output(output,text):
    ans = await call_check_only_statement_extraction(output,text)
    return ans

#prompt tuner
async def initial_extraction_prompt_tuner(prompt,output,text,failure_reason):
    ans = await call_improve_initial_extraction_prompt(prompt,output,text,failure_reason)
    return ans

#choose best prompt out of list of effective prompts for agentic extraction
async def choose_best_extraction_prompt(list_of_prompts):
    """Call th async extraction selector to choose best prompt in the list"""
    return await call_selector_initial_extraction_async(list_of_prompts)


#chooses best prompt according to history else generates a new prompt for extraction
def evaluator_extractor(old_prompt,output,text,collection,failure_reason):
    list_of_prompts=get_effective_prompts(uri,db.name,collection)
    #try to select from list of prompts that are effective first
    if list_of_prompts:  # Checks if list is not empty
        list_of_prompts = str(list_of_prompts)
        try:
            new_prompt = asyncio.run(choose_best_extraction_prompt(list_of_prompts))
            print(f'New prompt:{new_prompt}')
        except Exception as e:
            print(f"Error in async call_selector_async: {e}")
            new_prompt = old_prompt  # Fall back to the old prompt
    #generate prompts not in list of effective prompts (may generate a repeat prompt but not in list of effective)
    else:
        try:
            new_prompt = asyncio.run(initial_extraction_prompt_tuner(old_prompt,output,text,failure_reason))
        except Exception as e:
            print(f"Error in async generating improved extraction prompt: {e}")
            new_prompt = old_prompt  # Fall back to the old prompt
    return new_prompt

#add effectiveness state for used prompt for extraction workflow
def effectiveness_state_extraction(evaluate,prompt,collection):
    """
    Updates the effectiveness state of a prompt based on how good the prompt is as decided by another agent.

    Args:
    evaluate: LLM response to how effective prompt is
    prompt: prompt used currenly to check
    """
    if evaluate=='Y':
        # Prompt was effective, mark it as effective
        change_prompt_state_or_add(uri, db.name, collection, prompt, effective='Y')
    else:
        # Prompt was not effective, mark it as not effective
        change_prompt_state_or_add(uri, db.name, collection, prompt, effective='N')

"""Normal statement extractor split into steps"""
#statement extractor w no format
async def extract_no_format(text):
    ans=await call_pre_check_async(text)
    return ans

#statement extractor no format checker
async def check_extract_no_format(output,text):
    ans=await call_check_pre_check_async(output,text)
    return ans

#format corrected extraction
async def format_extract(output):
    ans=await call_format_async(output)
    return ans
