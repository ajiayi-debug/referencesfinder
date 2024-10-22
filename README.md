# Overview of References Finder:
Using Agentic RAG and semantic chunking to sanity check an article with cross ref and semantic scholar api as well as search for new references to update the article.
#### For more details, refer to the wiki of this project

## Diagram of workflow
<img width="713" alt="flowchart of current workflow 22102024" src="https://github.com/user-attachments/assets/abe4641e-2e93-4e4a-809f-24b57b43fb83">

## Legend
<img width="698" alt="legend 22102024" src="https://github.com/user-attachments/assets/002a64c0-6640-43b5-b3f6-0d27632c5ba1">

## Symbols
<img width="234" alt="database symbol" src="https://github.com/user-attachments/assets/4b8d4105-09a0-468a-94dd-4a8ed2cdd16f">

# Instructions for project (as of 10/22/2024)
## Installing dependencies
To start, install the required packages:

```sh
pip install -r requirements.txt
```

## Get access to openai group ad-group as well as install Azure cli tool 
#### (If you want to use other methods to call openai api, you will have to edit the functions accordingly (change azure to open ai))
### Accessing Azure CLI:
Download Azure CLI from [azure cli](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli)
### Finding Azure CLI:
Go to CMD and type `where az`.

Take note of the path with `./az.cmd`. You will need this path to create your .env file for azure endpoint.

## Finding token and endpoint
Token will automatically be created when running script while endpoint can be found in Azure AI Studios/ Resources and Keys/ Resource name/ </> View Code

## Inserting main PDF files:
A frontend will be built soon where you can just upload *1* article into the system.

## Inserting existing references:
Currently, users need to create a folder called 'text' in the main directory to insert reference articles referenced by the main paper. In future, a front end will be built for users to upload a whole folder / individual papers into the system.

## Finding version of api
Replace [version] with your version of api. This can be found in Azure AI Studios/ Resources and Keys/ Chat playground/ </> View Code 

## GPT model (agents, re-naming, keyword generation)
Take note that the prompt format only works for gpt 4 onwards. Replace [model] with gpt version. In my case, I used "gpt-4o". 

## Embedding model
An embedding model was also used. Replace [embed_model] with your embedding model. For my case, I used "text-embedding-3-large". 

## Certificate issues
I personally had no issues with the certificate (I just downloaded the certificate). However, if you do face issues, insert the path to certificate into [path to certificate]

## Create database using mongo db
Create your own personal cluster on [mongodb](https://www.mongodb.com/lp/cloud/atlas/try4?utm_source=google&utm_campaign=search_gs_pl_evergreen_atlas_core-high-int_prosp-brand_gic-null_apac-sg_ps-all_desktop_eng_lead&utm_term=mongodb&utm_medium=cpc_paid_search&utm_ad=e&utm_ad_campaign_id=19638458534&adgroup=149565726630&cq_cmp=19638458534&gad_source=1&gclid=CjwKCAjwnqK1BhBvEiwAi7o0Xz-PcC9hYm932vQTUV7QccPmGZg0i8gv6TRvhazhAsFCZRAzWzcslBoCC6QQAvD_BwE) and a database and insert uri into [mongodb]:

```
"mongodb+srv://<username>:<password>@<database>.n5tkni0.mongodb.net/?retryWrites=true&w=majority"
```

Replace <username> with username of database user, <password> with password of database user and <database> with database name created in cluster
## Create .env file
Replace [endpoint], [path to certificate], [version], [model], [embed_model], [mongodb] and [az cli] with the respective links and paths

```sh
endpoint = [endpoint]
az_path = [az cli]
ver=[version]
name=[model]
cert=[path to certificate]
embed_model=[embed_model]
uri_mongo=[mongodb]

```
## How to run:
### Articles to insert and folders to create (for now since frontend not created yet)
Insert the article you will like to update (main article) into a folder called 'main' which you will create in the main directory (outside [RAG](RAG)).
Insert the reference articles cited in the main article into a folder called 'text' which you will create in the main directory (outside [RAG](RAG)).
Insert any new reference you found that you thunk can update the main article into a folder called 'external_pdfs' which you will create in the main directory (outside [RAG](RAG)).

### RAG (backend)
#### Currently able to do a sanity check of main article as well as find new references and semantically check how much the new references support/oppose the statements (text that cites reference articles (i.e text(citation)) in the main article 

Run [RAG/gpt_retrieve_sieve.py](RAG/gpt_retrieve_sieve.py) to run the whole process from 
1) Finding the statements (text that cites reference articles (i.e text(citation)) and their cited reference article name, author and year the reference article is published from the main article uploaded in 'main' folder in main directory and send the infomation to mongo db
2) Embed then semantically chunk the reference articles uploaded into 'text' folder in the main directory and send the chunks to mongo db. The chunker used was the [Statistical Chunker](https://github.com/aurelio-labs/semantic-chunkers/blob/main/semantic_chunkers/chunkers/statistical.py). The embedding and chunking is done in parallel using async io and threads to reduce waiting time
3) Retrieve and 'Generate' (in our case we sieve the chunks as we just want to output the exact text/phrase/paragraph from the retrieved chunk of the reference article that was cited the in the main article) using our agent, which in this case is gpt 4o, and send the outputs to mongo DB. (unranked for now). The gpt 4o calls are run in parallel using async io and threads to reduce waiting time. Call crossref api to check for existing reference article retractions or corrections. If any, results will be outputted as an excel file to the user (for now, inside [RAG](RAG)).
4) Use gpt 4o to generate keywords from statements, which are then inserted into semantic scholar api to return papers. Downloadable papers are then downloaded and stored in a folder called 'papers' in the main directory. Any additional papers in 'external_pdfs' will also be sent to 'papers' for further processing, so make sure you add papers in 'external_pdfs' BEFORE this process starts
5) Repeat of step 2 for new reference articles found
6) Retrieve and 'Generate' (in our case we sieve the chunks as we just want to output the exact text/phrase/paragraph from the retrieved chunk of the reference article that was cited the in the main article as well as label if the sieved portion supports or oppose the statement and finally, give a confidence score on how much the sieved portion supports or oppose the statement. Take note the statement was converted to keywords which are then used to search for the reference articles.) using our agent, which in this case is gpt 4o.  The gpt 4o calls are run in parallel using async io and threads to reduce waiting time. *Next steps will be to only take top 5 results of each statement and new reference article and send to mongo db*

#### Near Future
1) To run a frontend
2) To be able to let experts choose which reference to use to update main article
3) To be able to let expert choose which sieved portions to use to update main article ( by letting gpt 4o created a new statement from the portions ) if necessary (e.g the opposing sieved portions are more increminating)
4) To output a final .txt or .pdf file with texts
