# Overview of References Finder:
To find the references and related references to update previous references in PDFs OR if latest reference found to debunk previous reference, update PDF by writing additional texts as well as update the references. 

# Instructions for project (as of 29/7/2024)
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
This part is only necessary if your device cannot find the path to Azure CLI. 

Go to CMD and type `where az`.

Take note of the path with `./az.cmd`. You will need this path to create your .env file

## Finding token and endpoint
Token will automatically be created when running script while endpoint can be found in Azure AI Studios/ Resources and Keys/ Resource name/ </> View Code
## Encrypting PDF files:
Replace [PDF] in .env file with the name of the PDFs. Try to place the PDFs in main directory. A future database will be set up.

## Finding version
Take note that the prompt format only works for gpt 4 onwards. Replace [model] with gpt version. In my case, I used "gpt-4o". Replace [version] with your version of model. This can be found in Azure AI Studios/ Resources and Keys/ Deployments/ name of model. In my case, I used "2024-02-01"

An embedding model was also used. Replace [embed_model] with your embedding model. For my case, I used "text-embedding-3-large". Take note that if you use any other models, the chunking size needs to be changed under the function chunking(dataframe, name of column to chunk, token size to chunk to) in [call_library](RAG/call_library.py) .

## Getting google api key and google cse id
Go to [Google api search](https://developers.google.com/custom-search/v1/overview) and request for an api key. Replace [google api key] in .env file with the received key.

Go to [Google CSE id creation](https://programmablesearchengine.google.com/controlpanel/create) and create a cse id. Replace [google cse id] in .env file with the received cse id.


## Certificate issues
I personally had no issues with the certificate (I just downloaded the certificate). However, if you do face issues, insert the path to certificate into [path to certificate]

## database using mongo db
Create your own personal cluster on [mongodb](https://www.mongodb.com/lp/cloud/atlas/try4?utm_source=google&utm_campaign=search_gs_pl_evergreen_atlas_core-high-int_prosp-brand_gic-null_apac-sg_ps-all_desktop_eng_lead&utm_term=mongodb&utm_medium=cpc_paid_search&utm_ad=e&utm_ad_campaign_id=19638458534&adgroup=149565726630&cq_cmp=19638458534&gad_source=1&gclid=CjwKCAjwnqK1BhBvEiwAi7o0Xz-PcC9hYm932vQTUV7QccPmGZg0i8gv6TRvhazhAsFCZRAzWzcslBoCC6QQAvD_BwE) and a database and insert uri into [mongodb]:

```
"mongodb+srv://<username>:<password>@<database>.n5tkni0.mongodb.net/?retryWrites=true&w=majority"
```
Replace <username> with username of database user, <password> with password of database user and <database> with database name created in cluster
## Create .env file
Replace [endpoint], [google api key], [PDF], [path to certificate], [google cse id], [version], [model], [embed_model], [mongodb] and [az cli] with the respective links and paths

```sh
endpoint = [endpoint]
googleapikey= [google api key]
az_path = [az cli]
PDF= [PDF]
googlecseid=[google cse id]
ver=[version]
name=[model]
cert=[path to certificate]
embed_model=[embed_model]
uri_mongo=[mongodb]

```
## How to run:

### RAG (main way of working for now)
Create a folder called text in the main directory and add all reference articles into it (in PDF format for now).

Add the main article (PDF format) into main directory and change the [PDF] relative path to the main article's name (pdfname.pdf) in .env file that you created.

Run [process_library.py](RAG/process_library.py) to process all reference articles.

Run [embed_and_call.py](RAG/embed_and_call.py) to call the gpt to access the reference articles to see if the main article did indeed reference them after embedding processed documents. This only embeds but does not process embeddings as through experimentations realise that directly sending the whole article into gpt 4o performs better than cosine similiarity. 

Run [call.py](RAG/call.py) to call the gpt to access the reference articles to see if main article did indeed reference them ONLY (this process is faster and recommended.)

Your output should be an excel file called find_ref.xlsx (if use embeddings) or find_ref_non_embed.xlsx (if no embeddings) with the following column names:

`reference article name: name of article that is referenced in main article`

`reference text in main article: text in main article that references reference article`

`reference text in reference article: what the reference text in the main article is referencing in the reference article`

### test 
#### (Outdated way of working, but still good for general reference on how to call gpt and how to connect gpt to google)
Replace [PDF] with the main article name (pdf_name.pdf)

Run [main.py](test/main.py). You will see an excel file called output.xlsx containing a summary for each article referenced in the PDF as well as the created query by gpt to input into google search. 

[gpt.py](test/gpt.py) and [pdftotext.py](test/pdftotext.py) contains all main functions used. 

[gptapiinternet.py](test/gptapiinternet.py) provides a reference on how to connect gpt api to google 
