# Instructions for project
Number of files to create: 2

environment.py

filenames.py

## Get access to openai group ad-group as well as install Azure cli tool
### Accessing Azure CLI:
Download Azure CLI from [azure cli](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli)
### Finding Azure CLI:
Go to CMD and type `where az`.
Take note of the path with `./az.cmd`. You will need this path to create your environment.py

### Finding token and endpoint
Token can be automatically created using environment.py script while endpoint can be found in Azure AI Studios/ Resources and Keys/ Resource name/ </> View Code

### Create environment.py
Replace [endpoint] and [az cli] with the respective links and paths
```sh
import os
import subprocess

az_path = r[path to az cli]

result = subprocess.run([az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()

os.environ['OPENAITOKEN'] = token
tok=token
endpoint = [endpoint]

```

Run the environment.py script before running anything else. Do re-run environment.py every hour or so as the token refreshes every hour

### Certificate issues
I personally had no issues with the certificate (I just downloaded the certificate). However, if you do face issues, insert the following code into environment.py:
`os.environ['REQUESTS_CA_BUNDLE'] = [path to certificate]`
You may access the certificate from the relevant parties

## Extracting info from PDF (Create filenames.py)
[images](https://medium.com/@alexaae9/python-how-to-extract-images-from-pdf-documents-9492a767a613#6a19)

## Encrypting PDF files:
Create filenames.py before running main.py. Input the PDF as follows:
```sh
PDF="pdf relative path"
```
Make sure to place the PDFs in the main directory 
