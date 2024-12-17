# **References Finder**
**Note** Until I get access to service principal access in azure, I am unable to dockerise the application due to the inability to automate token refresh without service principal access
## **Overview**
The **References Finder** project aims to automate the updating process of non-branded educational articles for **FrieslandCampina (FC) Institute**. By leveraging **semi-agentic Retrieval-Augmented Generation (RAG)**, **Agentic Search** and **semantic chunking**, the project addresses the challenges of manual reference management. This approach reduces both **time and financial costs** involved in outsourcing to vendors and the manual effort of reading and validating scientific articles.
### For more information on experiments run on the differing methods and/or the detailed explanation on the methods, please refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki) of this repository
---
## **Key features**
### **Agentic Components**

#### 1. **Semi-Agentic RAG**
The **retrieval, sieving and ranking agent** decides which of the semantic chunk to retrieve and sieve, but lacks the iterative, refinement process of a truly agentic agent

#### 2. **Agentic Search**
The **fully agentic search capability** will autonomously refine the **keyword search process**. If new papers (or semantic chunks) do not meet a confidence score threshold or no relevant papers are found to support a statement, the system will **retry by adjusting the keyword generator prompt**. This iterative approach aims to optimize retrieval and sieving for higher accuracy without human intervention.

### **User experience**

#### 1. **Easy updating of article using frontend interface**
The frontend allows users to **Automate checking exisiting references and finding new references while away** with **a click of a button**. It also allows users to **edit the article with just a few clicks**

### **Semantic Chunking**
#### 1. **Aurelio labs Semantic Chunker** 
From comparison of the available semantic chunkers, Aurelio Labs semantic chunker was chosen. For more details, refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki/3-Workflow-%E2%80%90-Existing-reference-articles)

---

## **Task Background**
The FC Institute recurringly incurs significant costs (~5000 euros per topic update) by outsourcing the review and update of articles to external vendors. The process involves:
1. **Manual search** for new references relevant to main article.
2. **Manual Reading** for new references relevant to main article.
3. **Manual Reference citing** for text to be updated with new reference and cited with new reference
4. **Verification** of existing references to ensure none have been retracted or corrected.  
5. **Article updates** based on new evidence where necessary.

---

## **Proposed Solution**
This project offers **semi-automated updates** for both references and article content, providing a more cost-effective and efficient solution. 

### Key Benefits:
- **Automated Reference Retrieval:** Identifies new relevant references using **Semantic Scholar API**.  
- **Verification of Existing References:** Checks for retractions and corrections via **Crossref API**.  
- **Cost Savings:** Minimizes dependency and hence cost on external vendors.
- **Time Savings:** Minimizes time taken to update articles

---

## **Impact**
The automation of reference management and article updates enables FC Institute to:
- **Save time** by streamlining the reference search and validation process.
- **Reduce costs** by decreasing reliance on outsourced vendors.
- **Improve accuracy** with reliable reference validation through APIs as well as reduce human error.
  
---

## **Future Directions**
- Fine-tuning of agents for more accurate retrieval, sieving, scoring and search
- A larger database to store different articles and all their related data such as old and new reference papers and their chunked content
- Automation of final article edits instead of relying on experts in the event experts are unavailable (though not advised due to potential hallucination of LLMs)
---
## Architecture of workflow
![image](https://github.com/user-attachments/assets/621b1133-5ff1-4079-ba39-24afd79c6ac1)

### Tech stack:
![image](https://github.com/user-attachments/assets/ddc8a7a4-d1fa-4501-9191-15a6c0fb0de2)

# Instructions for project (as of 11/12/2024)
### Frontend set up
Download node.js from [node.js](https://nodejs.org/en)

## Get access to openai group ad-group as well as install Azure cli tool 
#### (If you want to use other methods to call openai api, you will have to edit the functions accordingly (e.g change azure to open ai))
### Accessing Azure CLI:
Download Azure CLI from [azure cli](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli)
### Finding Azure CLI:
Go to CMD and type `where az`.

Take note of the path with `./az.cmd`. You will need this path to create your .env file for azure endpoint.

## Finding token and endpoint
Token will automatically be created when running script while endpoint can be found in Azure AI Studios/ Resources and Keys/ Resource name/ </> View Code

## Finding version of GPT api
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

## APIs 
The apis used in this project are from Semantic Scholar and CrossRef. CrossRef has a public API so we do not need to worry about access requirements since we can just call it in the script. For Semantic Scholar api, you will need to go to [semantic scholar](https://www.semanticscholar.org/product/api#api-key) and request for an api key. Then, replace [semantic_scholar_api] with the api key. 

## Create .env file
Replace [endpoint], [path to certificate], [version], [model], [embed_model], [mongodb], [semantic_scholar_api] and [az cli] with the respective links and paths

```sh
endpoint = [endpoint]
az_path = [az cli]
ver=[version]
name=[model]
cert=[path to certificate]
embed_model=[embed_model]
uri_mongo=[mongodb]
x-api-key=[semantic_scholar_api]
```

## Installing dependencies backend
In the root directory:

Install the required packages for backend:

```sh
pip install -r requirements.txt
```
## Installing dependencies frontend
Go to frontend directory from root directory

```sh
cd frontend
```

Install the required packages for frontend:

```sh
npm install
```

## **How to Run**
1) **Backend:** In root directory, run
   ```sh
   uvicorn backend.main:app
   ```
   For testing, run
   ```sh
   uvicorn backend.main:app --reload
   ```
2) **Frontend:** In root directory, run
   ```sh
   cd frontend
   ```
   then
   ```sh
   npm run dev
   ```

### **Frontend**
#### **Overview**
The frontend allows non-technical users to run the code to:
1) Guide the agents in the correct direction
2) Run background tasks while performing other duties
3) Obtain a final output

#### **/**
Upload main article and reference article(s) to process. Edit extracted output in event LLM hallucinates
![image](https://github.com/user-attachments/assets/700b4b5c-9343-4996-beaf-819788551121)
![image](https://github.com/user-attachments/assets/9e67fe40-1d01-4a35-8297-1108623c0d2f)
![image](https://github.com/user-attachments/assets/3b359cfa-9b97-40cd-89ad-cb3465ce818a)
![image](https://github.com/user-attachments/assets/7c8686fc-aad7-4e85-ba09-e17aaa3b5ead)

#### **/processing**
Allow user to upload any new reference they have found that they want to check to see if they are relevant to main article. Check existing references for retractions and corrections and downloads an excel file for user to take note. Runs through finding new references and selecting those that are deemed valid for presentation. Notify user when whole process is done (in progress)
![image](https://github.com/user-attachments/assets/0fe92695-7af1-44c5-9f92-85859f1ceee9)
![image](https://github.com/user-attachments/assets/796f3e42-010b-4b01-bf34-2abbcd71b9bd)


#### **/select**
Allow user to select new reference papers that they deem as relevant to the main article and send for further processing.
![image](https://github.com/user-attachments/assets/4a2624c3-3b4d-459e-94fc-611bcb37b470)

#### **/udecide**
Allow user to use the new selected reference article to update the article based on 
1) Replacing old references with new references
2) Adding new references to exisiting statements
3) Adding edits together with new reference to back of statements in case of change in content
Then, use an LLM to edit the article based on the user's selected edits
![image](https://github.com/user-attachments/assets/9fd66f1b-0214-4dca-9dea-d33ecb4a1ef2)


#### **/fileviewer**
Allow user to see the difference in the article after the update together with the edits made to the article in table form. Allow user to regenerate the edit process, download the article and clear all edits. Also allow user to edit the article itself in event of LLM hallucination.
![image](https://github.com/user-attachments/assets/01b70809-cb64-4dcc-9b36-e763f0ee4365)
![image](https://github.com/user-attachments/assets/2f2b866b-54e7-472d-8f60-a01b40045762)

### **Backend**

#### **Overview**  
The backend checks the main article’s integrity, discovers new references, evaluates how these references support or contradict the article’s cited statements and searches for new reference papers as well as check their integrity, how they support or contradict the main articles' cited statements if the current papers are not sufficient (for more details, refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki/5-Workflow-%E2%80%90-Agentic-search-using-Agentic-AI)).

#### **/** 

1. **Extract Statements and References:**  

   Extracts cited text and reference details from the main article, storing them in MongoDB.

#### **/processing** 

1. **Chunk and Store Reference Articles:**  

   Reference PDFs from `text` are embedded and chunked using the [Statistical Chunker](https://github.com/aurelio-labs/semantic-chunkers/blob/main/semantic_chunkers/chunkers/statistical.py). MongoDB stores the output, with **async I/O and threading** optimizing the process.

2. **Retrieve and Sieve:**  

   GPT-4o matches chunks to statements, extracting exact text matches. Crossref API checks for retractions or corrections, with results saved to Excel.

3. **Retrieve top 5 paper chunks for each statement and paper:**

   Process the data to output the top 5 chunks per statement per paper per sentiment using **confidence score** given

4. **Keyword Generation & New References:**  

   GPT-4o generates keywords, triggering **Semantic Scholar API** searches. Downloadable papers are saved to the `papers` folder, alongside any PDFs added to `external_pdfs`.

5. **Process New References:**  
   Newly retrieved references undergo the same chunking process as in step 2.

6. **Sieve and Label:**  

   The agent extracts relevant chunks, labels them as **supporting or opposing**, and assigns **confidence scores**.

7. **Retrieve top 5 paper chunks for each statement and paper:**

   Process the data to output the top 5 chunks per statement per paper per sentiment using **confidence score** given

8. **Perform Agentic Search for poor performing statements:**

   Statements that do not have papers found or all papers found are poor will go through the search process again with a different prompt formulated by an evaluator agent for keyword generation.
   (Refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki/5-Workflow-%E2%80%90-Agentic-search-using-Agentic-AI) for more information)
9. **Retrieve top 5 paper chunks for each statement and paper:**

   Process the data to output the top 5 chunks per statement per paper per sentiment using **confidence score** given


#### **/select**

Presents relevant papers with top 5 chunks and a summary for the chunks based on how relevant the papers are to the statement. Allows users to select papers for edits to the main article

#### **/udecide**

Allows users to edit the main article with a click of a few buttons using gpt 4o

#### **/fileviewer**

Allows users to see the final output and edit if necessary.
