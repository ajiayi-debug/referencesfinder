# Instructions for project
## Installing dependencies
To start, install the required packages:

```sh
pip install -r requirements.txt
```

## Get access to openai group ad-group as well as install Azure cli tool
### Accessing Azure CLI:
Download Azure CLI from [azure cli](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli)
### Finding Azure CLI:
This part is only necessary if your device cannot find the path to Azure CLI. 

Go to CMD and type `where az`.

Take note of the path with `./az.cmd`. You will need this path to create your .env file

### Finding token and endpoint
Token can be automatically created using [gptapi.py](gptapi.py) script while endpoint can be found in Azure AI Studios/ Resources and Keys/ Resource name/ </> View Code

### Create .env file
Replace [endpoint], [google key], [PDF] and [az cli] with the respective links and paths

```sh
endpoint = [endpoint]
googlekey= [google key]
az_path = [az cli]
PDF= [PDF]

```

### Certificate issues
I personally had no issues with the certificate (I just downloaded the certificate). However, if you do face issues, insert the following code into gptapi.py:

```sh
os.environ['REQUESTS_CA_BUNDLE'] = [path to certificate]
```

as well as

```sh
cert=[path to certificate]
```

in the .env file


You may access the certificate from the relevant parties

## Encrypting PDF files:
Replace [PDF] in .env file with the relative path of the PDFs.Try to place the PDFs in the main directory. A future database will be set up.

## Getting google api key
Go to [Google api search](https://developers.google.com/custom-search/v1/overview) and request for an api key. Replace [google key] in .env file with the received key.
