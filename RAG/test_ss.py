from search_ss import *
from download_paper_ss import *
import asyncio

keywords = 'lactose, genetic variation, enzyme lactase, childhood'
fields = 'paperId,title,year,externalIds,openAccessPdf,isOpenAccess'
papers = total_search_by_keywords(keywords, year=2022, fields=fields)

print(papers)

external_id_list, filtered_metadata_list = preprocess_paper_metadata(papers)

print("Papers with external IDs but no PDF or open access:")
for item in external_id_list:
    print(item)

print("\nFiltered paper metadata:")
for item in filtered_metadata_list:
    print(item)


asyncio.run(download(filtered_metadata_list, 'pp_test'))

