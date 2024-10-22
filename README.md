# Overview of References Finder:
Using Agentic RAG and semantic chunking to sanity check an article with cross ref and semantic scholar api as well as search for new references and check if they can be used with semantic scholar api.
#### For more details, refer to the wiki of this project

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
#### (If device cannot find path to Azure CLI):
Go to CMD and type `where az`.

Take note of the path with `./az.cmd`. You will need this path to create your .env file

#### (If device can find path to Azure CLI):
in [gpt_rag](RAG/gpt_rag.py), line 19-23:

Change 

```
az_path = os.getenv("az_path")

# Fetch Azure OpenAI access token
result = subprocess.run([az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()
````

to 

````
result = subprocess.run(['az', 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()
````

## Finding token and endpoint
Token will automatically be created when running script while endpoint can be found in Azure AI Studios/ Resources and Keys/ Resource name/ </> View Code
## Inserting main PDF files:
Replace [PDF] in .env file with the name of the main article PDF. Place the main article (.pdf) in main directory.

## Finding version
Replace [version] with your version of api. This can be found in Azure AI Studios/ Resources and Keys/ Chat playground/ </> View Code 

## Chat completion model
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
Replace [endpoint], [PDF], [path to certificate], [version], [model], [embed_model], [mongodb] and [az cli] with the respective links and paths

```sh
endpoint = [endpoint]
# googleapikey= [google api key]
az_path = [az cli]
PDF= [PDF]
# googlecseid=[google cse id]
ver=[version]
name=[model]
cert=[path to certificate]
embed_model=[embed_model]
uri_mongo=[mongodb]

```
## How to run:

### RAG (backend)
#### Fact checking if articles cited in main article is valid
##### Done to validate existing references and workflow will be recycled to validate new references for updates
Create a folder called text in the main directory and add all reference articles into it (in PDF format for now).

Add the main article (PDF format) into main directory (outside [RAG](RAG) and change the [PDF] relative path to the main article's name (pdfname.pdf) in .env file that you created.

Run [process_and_embed.py](RAG/process_and_embed.py) to: 
1) Pre-process the reference articles (in pdf format) into .txt files
2) Use gpt4o to figure out the title of each reference article from their .txt files (if reference article text token length exceeds gpt4o context length (I set to 2000 tokens), split the reference article text into half then process the first half to figure out the name of the article)
3) Use semantic chunking from the following [chunker](https://github.com/aurelio-labs/semantic-chunkers) to chunk each reference article text according to semantic similiarity using text embedding 3 large. The chunker used was the [Statistical Chunker](https://github.com/aurelio-labs/semantic-chunkers/blob/main/semantic_chunkers/chunkers/statistical.py)
4) Embed the chunks using text embedding 3 large
5) Save the chunks and embedded chunks according to reference article title into MongoDB. The collection 'processed' contains reference article title and chunks only while the collection 'processed_and_embed' contains reference article title, chunks and the embedded chunks.

Run [call_after_embed.py](RAG/call_after_embed.py) to:
1) Pre-process the main article (in pdf format) to .txt 
2) Use gpt4o to find all cited references and the text that cites these references (will work on chunking main article in future to ensure that articles of all token lengths accepted, but in general as articles are meant for information sharing, will not be too large and most can be accepted)
3) For each text that cites references, find the reference title it cites, then embed the text using text embedding 3 large and calculate cosine similiarity between embedded text and each embedded chunk of the reference article cited by the text. (Retrieval Augmented Generation)
4) Return chunks that have cosine similiarity >0.5 (max 10, but usually does not exceed 10), ranked according to cosine similiarity (descendingly).
5) Use gpt4o to re-rank the chunks according to how semantically similiar text that cites the reference is to the chunk (Found that cosine similiarity not a good ranker in terms of semantic similiarity, but good at sieving out what chunks are semantically similiar and what chunks are not) (reasoning found in wiki)
6) Obtain top 3 chunks (to get rid of chunks that gpt 4o deems as not semantically similiar at all, ranked last or one of the last - occurs as maybe only a word or so semantically similiar in chunk and appears multiple times in chunk, causing cosine similiarity >0.5 when in actual fact its not semantically similiar to text in main article)
7) Send output to database in Mongo DB under 'find_ref'

Column names are:

![image](https://github.com/user-attachments/assets/18857146-5502-4c74-92b8-f5a9745ff5b5)



