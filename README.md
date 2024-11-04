# **References Finder**

## **Overview**
The **References Finder** project aims to automate the updating process of non-branded educational articles for **FrieslandCampina (FC) Institute**. By leveraging **semi-agentic Retrieval-Augmented Generation (RAG)** and **semantic chunking**, the project addresses the challenges of manual reference management. This approach reduces both **time and financial costs** involved in outsourcing to vendors and the manual effort of reading and validating scientific articles.
### For more information on experiments run on the differing methods, please refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki) of this repository
---
## **Key features**
### **Agentic Components**

#### 1. **Semi-Agentic RAG**
The **retrieval, sieving and ranking agent** decides which of the semantic chunk to retrieve and sieve, but lacks the iterative, refinement process of a truly agentic agent

#### 2. **Agentic Search**
The **fully agentic search capability** will autonomously refine the **keyword search process**. If new papers (or semantic chunks) do not meet a confidence score threshold or no relevant papers are found to support a statement, the system will **retry by adjusting the keyword generator prompt**. This iterative approach aims to optimize retrieval and sieving for higher accuracy without human intervention.

### **Semantic Chunking**
#### 1. **Aurelio labs Semantic Chunker** 
From comparison of the available semantic chunkers, Aurelio Labs semantic chunker was chosen. For more details, refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki/3-Workflow-%E2%80%90-Existing-reference-articles)

---

## **Task Background**
The FC Institute recurringly incurs significant costs (~5000 euros per topic update) by outsourcing the review and update of articles to external vendors. The process involves:
1. **Manual search** for new references relevant to main article.
2. **Manual Reading** for new references relevant to main article.
3. **Verification** of existing references to ensure none have been retracted or corrected.  
4. **Article updates** based on new evidence where necessary.

---

## **Proposed Solution**
This project offers **semi-automated updates** for both references and article content, providing a more cost-effective and efficient solution.

### Key Benefits:
- **Automated Reference Retrieval:** Identifies new relevant references using **Semantic Scholar API**.  
- **Verification of Existing References:** Checks for retractions and corrections via **Crossref API**.  
- **Automated Content Updates:** Suggests necessary modifications to the article text based on updated references.  **Note** A future update
- **Cost Savings:** Minimizes dependency on external vendors and reduces the need for in-house manual updates.

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
---

## Diagram of **Current** workflow
![image](https://github.com/user-attachments/assets/0e860536-d8f9-4b55-a492-6464ce1ba196)


## Legend
![image](https://github.com/user-attachments/assets/50d0a1bb-22ea-4421-9494-f707caedcd24)


## Symbols
![image](https://github.com/user-attachments/assets/185fb3c1-7f2f-4294-a767-1ced9900ca97)

![image](https://github.com/user-attachments/assets/e32db32f-e6d9-48c4-bf08-e537d347ee5a)

![image](https://github.com/user-attachments/assets/ac6f1277-9588-43e1-a38c-8b1aaa2bd95b)

![image](https://github.com/user-attachments/assets/074df774-1771-41af-9667-fe614070fcfd)


# Instructions for project (as of 04/11/2024)
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
The apis used in this project are from Semantic Scholar and CrossRef. CrossRef has a public API so we do not need to worry about it since we can just call it in the script. For Semantic Scholar api, you will need to go to [semantic scholar](https://www.semanticscholar.org/product/api#api-key) and request for an api key. Then, replace [semantic_scholar_api] with the api key. 

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

## **How to Run**

### **Set up Folders (Temporary, Before Frontend Implementation)**
1. **`main` Folder:**  
   Place the article you want to update in this folder. Create this folder in the main directory (outside the `RAG` folder).

2. **`text` Folder:**  
   Add reference articles cited in the main article here. Create this folder in the main directory.

3. **`external_pdfs` Folder:**  
   Add any additional references you believe can update the main article in this folder. Ensure it exists in the main directory before starting the process.

---

### **RAG (Backend)**

#### **Current Capabilities**  
The backend checks the main article’s integrity, discovers new references, evaluates how these references support or contradict the article’s cited statements and searches for new reference papers as well as check their integrity, how they support or contradict the main articles'cited statements if the currentpapers are not sufficient (for more details, refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki/5-Workflow-%E2%80%90-Agentic-search-using-Agentic-AI)).

Run [agentic_search_rag.py](RAG/agentic_search_rag.py) to execute the process: 

1. **Extract Statements and References:**  

   Extracts cited text and reference details from the main article, storing them in MongoDB.

2. **Chunk and Store Reference Articles:**  

   Reference PDFs from `text` are embedded and chunked using the [Statistical Chunker](https://github.com/aurelio-labs/semantic-chunkers/blob/main/semantic_chunkers/chunkers/statistical.py). MongoDB stores the output, with **async I/O and threading** optimizing the process.

3. **Retrieve and Sieve:**  

   GPT-4o matches chunks to statements, extracting exact text matches. Crossref API checks for retractions or corrections, with results saved to Excel.

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


#### **Near Future Plans**
1. **Develop a Frontend Interface:**

   Allow us to create table for next step as well as easy user interface
2. **Expert Selection of References:**  

   Allow experts to choose which references to use for updating the main article based on top 5 outputs. 
3. **Export Final Output:**  

   Generate a `.txt` or `.pdf` file with the updated article content.
