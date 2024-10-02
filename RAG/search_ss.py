from dotenv import load_dotenv
import os
import requests
import time
from typing import AsyncGenerator, Generator, Iterable, TypeVar, Union, List, Dict, Any, Optional, Tuple
import ast
load_dotenv()


def search_papers_by_keywords(keywords: str, year: int = None, exclude_name: str = None, fields: str = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess') -> dict:
    url = 'https://api.semanticscholar.org/graph/v1/paper/search'
    query_params = {'query': keywords, 'fields': fields}
    api_key = os.getenv('x-api-key')
    headers = {'x-api-key': api_key}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=query_params, headers=headers)

            # Check for rate limits and other errors
            if response.status_code == 429:
                print(f"Rate limit exceeded. Retrying in 60 seconds... Attempt {attempt + 1}/{max_retries}")
                time.sleep(60)
                continue
            elif response.status_code != 200:
                print(f"Request failed with status code {response.status_code}. Retrying in 60 seconds... Attempt {attempt + 1}/{max_retries}")
                time.sleep(60)
                continue

            response_data = response.json()

            if year:
                response_data['data'] = [
                    paper for paper in response_data.get('data', [])
                    if 'year' in paper and paper['year'] and str(paper['year']).isdigit() and int(paper['year']) >= int(year)
                ]
            if exclude_name:
                response_data['data'] = [
                    paper for paper in response_data.get('data', [])
                    if exclude_name.lower() not in paper.get('title', '').lower()
                ]


            return response_data

        except requests.exceptions.RequestException as e:
            print(f"Request exception occurred: {e}. Retrying in 60 seconds... Attempt {attempt + 1}/{max_retries}")
            time.sleep(60)

    print("Max retries exceeded.")
    return None

def total_search_by_keywords(keywords: str, year: int = None, exclude_name: str = None, fields: str = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess'):
    """
    Search for papers based on keywords and optionally filter results by publication year,
    then return a list of paper dictionaries from the search results.
    
    :param keywords: The search query for finding papers.
    :param year: Optional filter to include papers published after the specified year.
    :param fields: Comma-separated list of fields to be returned in the response.
    :return: A list of dictionaries containing paper metadata.
    """
    # Perform the search
    data = search_papers_by_keywords(keywords, year, exclude_name, fields)
    
    # Extract paper list
    paper_list = []
    if data:
        for paper in data.get('data', []):
            paper_list.append(paper)
    
    return paper_list

def total_search_by_grouped_keywords(keywords: str, year: int = None, exclude_name: str = None, fields: str = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess'):
    """
    Search for papers based on keywords and optionally filter results by publication year,
    then return a list of paper dictionaries from the search results.
    
    :param keywords: The search query for finding papers.
    :param year: Optional filter to include papers published after the specified year.
    :param fields: Comma-separated list of fields to be returned in the response.
    :return: A list of dictionaries containing paper metadata.
    """
    # Split the str version of list of grouped keywords into groups
    group_keyword=ast.literal_eval(keywords)
    paper_list=[]
    for kw in group_keyword:
        # Perform the search
        data = search_papers_by_keywords(kw, year, exclude_name, fields)
        
        # Extract paper list
        if data:
            for paper in data.get('data', []):
                paper_list.append(paper)
        
    return paper_list




def preprocess_paper_metadata(paper_metadata_list: List[Dict[str, Union[str, bool, dict]]]) -> Tuple[List[List[str]], List[Dict[str, Union[str, bool, dict]]]]:
    """
    Preprocess the paper metadata to find papers with an external ID but no open access or downloadable PDF,
    and exclude those papers from the original list.

    :param paper_metadata_list: List of paper metadata dictionaries.
    :return: A tuple containing:
        - List of lists with [paperId, externalId] for papers that meet the criteria.
        - Filtered list of paper metadata excluding those with an external ID but no PDF or open access.
    """
    external_id_list = []
    filtered_metadata_list = []

    for paper_metadata in paper_metadata_list:
        paper_id = paper_metadata.get('paperId')
        is_open_access = paper_metadata.get('isOpenAccess', False)
        open_access_pdf = paper_metadata.get('openAccessPdf')
        external_ids = paper_metadata.get('externalIds', {})

        if not is_open_access and open_access_pdf is None and external_ids:
            # Get the first available external ID from the dictionary
            external_id = next(iter(external_ids.values()), "External ID doesn't exist")
            external_id_list.append([paper_id, external_id])
            continue  # Skip adding this paper to the filtered list
        
        # If the paper does not meet the above condition, add it to the filtered list
        filtered_metadata_list.append(paper_metadata)

    return external_id_list, filtered_metadata_list

def extract_title(metadata_list: List[Dict[str, Any]]) -> List[str]:
    """Extract title from the metadata list."""
    return [paper['title'] for paper in metadata_list]

def extract_year(metadata_list: List[Dict[str, Any]]) -> List[str]:
    """Extract year from the metadata list."""
    return [paper['year'] for paper in metadata_list]



# # Example usage:
# keywords = 'lactose, genetic variation, enzyme lactase, childhood'
# fields = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess'
# papers = total_search_by_keywords(keywords, year=2022, fields=fields)

# print(papers)

# external_id_list, filtered_metadata_list = preprocess_paper_metadata(papers)

# print("Papers with external IDs but no PDF or open access:")
# for item in external_id_list:
#     print(item)

# print("\nFiltered paper metadata:")
# for item in filtered_metadata_list:
#     print(item)


def get_paper_id_by_title(title, api_key=os.getenv('x-api-key')):
    """
    Retrieve the paper ID from Semantic Scholar based on the paper title.

    Args:
        title (str): The title of the paper to search for.
        api_key (str, optional): The Semantic Scholar API key.

    Returns:
        str: The paper ID if found, otherwise None.
    """
    # Base URL for Semantic Scholar API
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Prepare the request headers
    headers = {
        "Accept": "application/json",
        "x-api-key": api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    }

    # Prepare the query parameters
    params = {
        "query": title,
        "fields": "paperId,title",
        "limit": 1  # Limit to 1 result
    }

    # Send the GET request to the Semantic Scholar API
    response = requests.get(base_url, headers=headers, params=params)
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            # Return the first paper ID found
            return data['data'][0]['paperId']
        else:
            print("No paper found with the given title.")
            return None
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def get_title_by_title(title, api_key=os.getenv('x-api-key')):
    """
    Retrieve the paper ID from Semantic Scholar based on the paper title.

    Args:
        title (str): The title of the paper to search for.
        api_key (str, optional): The Semantic Scholar API key.

    Returns:
        str: The paper ID if found, otherwise None.
    """
    # Base URL for Semantic Scholar API
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Prepare the request headers
    headers = {
        "Accept": "application/json",
        "x-api-key": api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    }

    # Prepare the query parameters
    params = {
        "query": title,
        "fields": "paperId,title",
        "limit": 1  # Limit to 1 result
    }

    # Send the GET request to the Semantic Scholar API
    response = requests.get(base_url, headers=headers, params=params)
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            # Return the first paper ID found
            return data['data'][0]['title']
        else:
            print("No paper found with the given title.")
            return None
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


