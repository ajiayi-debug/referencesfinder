#!/usr/bin/env python3
import aiohttp
import asyncio
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()

# Function to fetch metadata for a single paper ID
async def fetch_paper_metadata(paper_id: str, api_key: str) -> Optional[Dict[str, str]]:
    """
    Fetch metadata for a given paper ID from the Semantic Scholar API and return the open access PDF URL if available.
    
    :param paper_id: The ID of the paper to search for.
    :param api_key: API key for accessing Semantic Scholar API.
    :return: A dictionary with paper ID and open access PDF URL or None if not found.
    """
    url = f'https://api.semanticscholar.org/graph/v1/paper/{paper_id}'
    headers = {
        'X-API-KEY': api_key,
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                pdf_url = data.get('openAccessPdf', {}).get('url', None)
                external_ids = data.get('externalIds', {})
                return {
                    'paperId': paper_id,
                    'pdfUrl': pdf_url,
                    'externalIds': external_ids
                }
        except aiohttp.ClientError as e:
            print(f"Error fetching metadata for paper ID '{paper_id}': {e}")
            return None

# Function to fetch metadata for a list of paper IDs
async def fetch_papers_metadata(paper_ids: List[str], api_key: str) -> List[Dict[str, Optional[str]]]:
    """
    Fetch metadata for a list of paper IDs.
    
    :param paper_ids: List of paper IDs to search for.
    :param api_key: API key for accessing Semantic Scholar API.
    :return: List of dictionaries with paper ID and open access PDF URL.
    """
    tasks = [fetch_paper_metadata(paper_id, api_key) for paper_id in paper_ids]
    results = await asyncio.gather(*tasks)
    return [result for result in results if result is not None]

# Main function to run the script
async def main():
    API_KEY = os.getenv('x-api-key')  # Ensure you have the API key in your environment variables

    if not API_KEY:
        print("API key not found. Please set 'S2_API_KEY' in your environment variables.")
        return

    # List of paper IDs to fetch metadata for
    paper_ids = [
        '32b6a7c72f38447727bfae3ef0fbda5061653d6d'
        # Add more paper IDs here
    ]

    # Fetch metadata for the paper IDs
    metadata_list = await fetch_papers_metadata(paper_ids, API_KEY)

    # Print out the metadata
    for metadata in metadata_list:
        print(metadata)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
