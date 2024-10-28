import subprocess
import logging
import os
from dotenv import load_dotenv
load_dotenv()

def get_azure_access_token():
    try:
        logging.info("Fetching Azure OpenAI access token...")
        az_path = os.getenv("az_path", "az")
        # Use the absolute path to ensure Python finds the executable correctly
        result = subprocess.run(
            [
                az_path,
                "account", "get-access-token", "--resource",
                "https://cognitiveservices.azure.com", "--query", "accessToken", "-o", "tsv"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15  # Prevent hanging
        )

        if result.returncode != 0:
            error_message = result.stderr.decode('utf-8').strip()
            logging.error(f"Failed to fetch access token: {error_message}")
            return None

        # Decode the token and return it
        token = result.stdout.decode('utf-8').strip()
        logging.info("Azure OpenAI access token retrieved successfully.")
        return token

    except subprocess.TimeoutExpired:
        logging.error("Fetching access token timed out.")
        return None
    except FileNotFoundError:
        logging.error("Azure CLI executable not found. Please ensure Azure CLI is installed and added to PATH.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching access token: {e}")
        return None

# Test the function
if __name__ == "__main__":
    token = get_azure_access_token()
    if token:
        print(f"Access Token: {token}")
    else:
        print("Failed to retrieve access token.")
