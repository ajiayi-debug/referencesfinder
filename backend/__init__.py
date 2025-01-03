import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)

logging.info("Starting initialization...")

from .mongo_client import *
logging.info("mongo_client imported successfully.")
from .call_mongodb import *
logging.info("call_mongodb imported successfully.")
from .expert_decision import formatting,merge_old_new,make_pretty_for_expert,make_summary_for_comparison
logging.info("expert_decision imported successfully.")
from .gpt_rag_asyncio import *
logging.info("gpt_rag_asyncio imported successfully.")
from .semantic_chunking import *
logging.info("semantic chunking imported successfully.")
from .process_and_embed import *
logging.info("process_and_embed imported successfully.")
from .gpt_retrievesieve import retrieve_sieve_references,retrieve_sieve_references_new,cleaning,add_to_existing,cleaning_initial
logging.info("gpt_retrievesieve imported successfully.")
from .semantic_scholar_keyword_search import search_and_retrieve_keyword,search_and_retrieve_keyword_agentic
logging.info("semantic_scholar_keyword_search imported successfully.")
from .process_ref import *
logging.info("process_ref imported successfully.")
from .pdf import *
logging.info("pdf imported successfully.")
from .gpt_rag import get_names,read_text_file,get_references,similiar_ref,clean_responses,rank_and_check,summarise_subdocument,locate_subdoc
logging.info("gpt_rag imported successfully.")
from .semantic_chunking import process_dataframe_sc1
logging.info("semantic_chunking imported successfully.")
from .download_paper_ss import process_and_download
logging.info("download_paper_ss imported successfully.")
from .search_ss import total_search_by_grouped_keywords,preprocess_paper_metadata,extract_title,extract_author,extract_year
logging.info("search_ss imported successfully.")
from .agent import evaluator,effectiveness_state
logging.info("agent imported successfully.")
from .models import *
logging.info("models imported successfully")
from .agentic_initial_check import *
logging.info("agentic initial check imported successfully")
from .match import *
logging.info('match imported successfully')
from .token_manager import *
logging.info('token_manager imported successfully')
