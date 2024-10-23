# **References Finder Project**

## **Overview**
The **References Finder** project aims to automate the updating process of non-branded educational articles for **FrieslandCampina (FC) Institute**. By leveraging **semi-agentic Retrieval-Augmented Generation (RAG)** and **semantic chunking**, the project addresses the challenges of manual reference management. This approach reduces both **time and financial costs** involved in outsourcing to vendors and the manual effort of reading and validating scientific articles.
### For more information on experiments run on the differing methods, please refer to the [wiki](https://github.com/ajiayi-debug/referencesfinder/wiki) of this repository
---

## **Components**

### 1. **Agentic Component (Future Implementation)**
The **fully agentic search capability** will autonomously refine the **keyword search process**. If new papers (or semantic chunks) do not meet a confidence score threshold or no relevant papers are found to support a statement, the system will **retry by adjusting the keyword generator prompt**. This iterative approach aims to optimize retrieval and sieving for higher accuracy without human intervention.

- **Note:** This feature is currently on hold due to issues with Azure resources.

### 2. **Semi-Agentic Component (Current Implementation)**
The **retrieval and sieving agent** decides which of the semantic chunk to retrieve and sieve, but lacks the iterative, refinement process of a truly agentic agent

---

## **Problem Statement**
The FC Institute currently incurs significant costs (~5000 euros per topic update) by outsourcing the review and update of references to external vendors. The process involves:
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
- **Improve accuracy** with reliable reference validation through APIs.
  
---

## **Future Directions**
- Implement **fully agentic search capabilities** once Azure OpenAI resources become available.
- Expand automation to cover a wider range of article types and more complex updates.

---

## Diagram of **Current** workflow
<img width="714" alt="flowchart of current workflow 22102024" src="https://github.com/user-attachments/assets/89e7ca03-bdc1-4e56-93b1-b2b0da58055e">

## Legend
<img width="698" alt="legend 22102024" src="https://github.com/user-attachments/assets/002a64c0-6640-43b5-b3f6-0d27632c5ba1">

## Symbols
<img width="234" alt="database symbol" src="https://github.com/user-attachments/assets/4b8d4105-09a0-468a-94dd-4a8ed2cdd16f">
<img width="130" alt="paper symbol" src="https://github.com/user-attachments/assets/41421712-738d-486b-a492-96ff89b27fb3">

# Instructions for project (as of 22/10/2024)
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
## **How to Run**

### **Set up Folders (Temporary, Before Frontend Implementation)**
1. **`main` Folder:**  
   Place the article you want to update in this folder. Create it in the main directory (outside the `RAG` folder).

2. **`text` Folder:**  
   Add reference articles cited in the main article here. Create this folder in the main directory.

3. **`external_pdfs` Folder:**  
   Add any additional references you believe can update the main article in this folder. Ensure it exists in the main directory before starting the process.

---

### **RAG (Backend)**

#### **Current Capabilities**  
The backend checks the main article’s integrity, discovers new references, and evaluates how these references support or contradict the article’s cited statements.

Run [gpt_retrieve_sieve.py](RAG/gpt_retrieve_sieve.py) to execute the process: 

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

*Next Steps: Prioritize the top 5 results per statement and store them in MongoDB.*


#### **Near Future Plans**
1. **Agentic Search Implementation:**  
   Retry searches if the retrieved chunks don’t meet a confidence threshold or return no results. A re-evaluator agent will refine keyword generation prompts.

2. **Develop a Frontend Interface.**  
3. **Expert Selection of References:**  
   Allow experts to choose which references to use for updating the main article.

4. **Expert Selection of Sieved Portions:**  
   Experts can review sieved portions and instruct GPT-4o to create new statements based on opposing or critical content.

5. **Export Final Output:**  
   Generate a `.txt` or `.pdf` file with the updated article content.
