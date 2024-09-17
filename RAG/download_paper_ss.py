#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

from aiohttp import ClientSession
import argparse
import asyncio
from itertools import islice
import os
from typing import AsyncGenerator, Generator, Iterable, TypeVar, Union, List, Dict, Any, Optional, Tuple
from tqdm.asyncio import tqdm as tqdm_asyncio
from bs4 import BeautifulSoup

S2_API_KEY = os.environ['x-api-key']

T = TypeVar('T')

def batched(iterable: Iterable[T], n: int) -> Generator[list[T], None, None]:
    "Batch data into tuples of length n. The last batch may be shorter."
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while (batch := list(islice(it, n))):
        yield batch

def extract_paper_ids(metadata_list: List[Dict[str, Any]]) -> List[str]:
    """Extract paper IDs from the metadata list."""
    return [paper['paperId'] for paper in metadata_list]

async def get_papers(session: ClientSession, paper_ids: list[str], batch_size = 500, fields: str = 'paperId,title', **kwargs) -> AsyncGenerator[dict, None]:
    for batch in batched(paper_ids, batch_size):
        params = {
            'fields': fields,
            **kwargs,
        }
        headers = {
            'X-API-KEY': S2_API_KEY,
        }
        json = {
            'ids': batch,
        }

        async with session.post(f'https://api.semanticscholar.org/graph/v1/paper/batch', params=params, headers=headers, json=json) as response:
            response.raise_for_status()

            for paper in await response.json():
                yield paper

async def download_pdf(session: ClientSession, url: str, path: str, non_pdf_folder: str, user_agent: str = 'aiohttp/3.0.0') -> Optional[str]:
    headers = {
        'user-agent': user_agent,
    }

    # Define the temporary file path
    temp_path = path + '.temp'
    
    # Check if file already exists
    if os.path.exists(path):
        print(f"File already exists: '{path}'")
        return None

    async with session.get(url, headers=headers, verify_ssl=False) as response:
        response.raise_for_status()

        # Save the content to a temporary file
        with open(temp_path, 'wb') as f:
            async for chunk in response.content.iter_chunked(8192):
                f.write(chunk)

        # Check the content type
        content_type = response.headers.get('content-type', '')
        if 'application/pdf' not in content_type:
            # Save non-PDF content to a separate folder
            os.makedirs(non_pdf_folder, exist_ok=True)
            non_pdf_path = os.path.join(non_pdf_folder, os.path.basename(path))
            os.rename(temp_path, non_pdf_path)
            print(f"Content is not a PDF, saved to '{non_pdf_path}'")
            return non_pdf_path

        # Rename the temporary file to a PDF
        os.rename(temp_path, path)
        print(f"Downloaded file to '{path}'")
        return path

async def download_page(session: ClientSession, url: str, path: str) -> Optional[str]:
    headers = {
        'user-agent': 'aiohttp/3.0.0',
    }

    async with session.get(url, headers=headers, verify_ssl=False) as response:
        response.raise_for_status()

        # Save the HTML content
        with open(path, 'wb') as f:
            async for chunk in response.content.iter_chunked(8192):
                f.write(chunk)
        
        print(f"Downloaded HTML page to '{path}'")
        return path

def extract_text_from_html(html_path: str) -> str:
    """Extract text from an HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        return soup.get_text(separator='\n')

async def download_papers(paper_ids: list[str], directory: str, batch_size: int = 500, user_agent: str = 'aiohttp/3.0.0') -> AsyncGenerator[tuple[str, Union[str, None, Exception]], None]:
    os.makedirs(directory, exist_ok=True)

    async with ClientSession() as session:
        async for paper in get_papers(session, paper_ids, batch_size=batch_size, fields='paperId,isOpenAccess,openAccessPdf'):
            paper_id = paper['paperId']
            try:
                # Check if the paper has an openAccessPdf field and a valid URL
                if 'openAccessPdf' in paper and paper['openAccessPdf'] and 'url' in paper['openAccessPdf']:
                    pdf_url: str = paper['openAccessPdf']['url']
                    pdf_path = os.path.join(directory, f'{paper_id}.pdf')
                    result = await download_pdf(session, pdf_url, pdf_path, directory)
                    yield paper_id, result
                else:
                    # Check if it's an HTML page
                    html_url = paper.get('url')  # Replace with actual field if available
                    if html_url:
                        html_path = os.path.join(directory, f'{paper_id}.html')
                        result = await download_page(session, html_url, html_path)
                        # Extract text from the downloaded HTML page
                        text = extract_text_from_html(html_path)
                        # Save the extracted text if needed, or handle it further
                        text_path = os.path.join(directory, f'{paper_id}.txt')
                        with open(text_path, 'w', encoding='utf-8') as f:
                            f.write(text)
                        yield paper_id, text_path
                    else:
                        # Yield None if no valid URL is available
                        yield paper_id, None
            except Exception as e:
                # Yield the paper ID and the exception if an error occurs
                yield paper_id, e

async def download(metadata_list: List[Dict[str, Any]], directory: str, batch_size: int = 500, user_agent: str = 'aiohttp/3.0.0') -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    paper_ids = extract_paper_ids(metadata_list)
    total_papers = len(paper_ids)
    
    failed_downloads = []
    successful_downloads = []

    async for paper_id, result in tqdm_asyncio(download_papers(paper_ids, directory=directory, batch_size=batch_size, user_agent=user_agent), total=total_papers, desc="Downloading papers", ncols=100):
        if isinstance(result, Exception):
            # Capture the reason for failure
            failed_downloads.append({
                'paper_id': paper_id,
                'error': str(result)
            })
        elif result is None:
            # File already exists; do nothing
            pass
        else:
            successful_downloads.append({
                'paper_id': paper_id,
                'path': result
            })

    return failed_downloads, successful_downloads

async def process_and_download(filtered_metadata_list, directory):
    failed_downloads, successful_downloads = await download(filtered_metadata_list, directory)
    
    # Print or process the list of failed downloads
    print("Failed downloads:")
    for failure in failed_downloads:
        print(f"Failed to download '{failure['paper_id']}': {failure['error']}")

    # Optionally: Return the lists if you need to use them later
    return failed_downloads, successful_downloads



# if __name__ == '__main__':
#     # Example metadata list
#     paper_metadata_list = [
#         {'paperId': '0f5f83d40b55d04b0c259f4538b1b55a3141dea0', 'externalIds': {'DOI': '10.1002/bies.202200243', 'CorpusId': 258238766, 'PubMed': '37075758'}, 'title': 'Proposed mechanism for the selection of lactase persistence in childhood', 'year': 2023, 'isOpenAccess': True, 'openAccessPdf': {'url': 'https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/bies.202200243', 'status': 'HYBRID'}},
#         {'paperId': '820373f462d545a6669134bff467cb0eb7254133', 'externalIds': {'DOI': '10.12775/jehs.2024.69.49393', 'CorpusId': 269887302}, 'title': 'Lactase Deficiency and Lactose Intolerance: Current Understanding and Future Directions', 'year': 2024, 'isOpenAccess': True, 'openAccessPdf': {'url': 'https://apcz.umk.pl/JEHS/article/download/49393/38556', 'status': 'GOLD'}},
#         {'paperId': '35a9462b1ef7c513d61811907016a0452906384a', 'externalIds': {'DOI': '10.1093/ecco-jcc/jjad212.0449', 'CorpusId': 267251685}, 'title': 'P319 Genetic polymorphism of lactose intolerance in patients with Inflammatory Bowel Disease', 'year': 2024, 'isOpenAccess': True, 'openAccessPdf': {'url': 'https://academic.oup.com/ecco-jcc/article-pdf/18/Supplement_1/i703/56347667/jjad212.0449.pdf', 'status': 'BRONZE'}}
#     ]

#     asyncio.run(process_and_download(paper_metadata_list, 'pp_test'))
