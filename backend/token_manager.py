# token_manager.py

import asyncio
import os
import time
import logging
from dotenv import load_dotenv
import subprocess
"""Universal token manager"""
# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Azure configuration
endpoint = os.getenv("endpoint")
api_version = os.getenv("ver")
az_path = os.getenv("az_path", "az")  # Default to 'az' if not specified

class TokenManager:
    def __init__(self):
        self.access_token = None
        self.token_expiry_time = None
        self.token_lock = asyncio.Lock()  # Use asyncio.Lock
        self.refresh_in_progress = asyncio.Event()
        self.refresh_in_progress.clear()
        self.azure_endpoint = endpoint
        self.api_version = api_version
        self.az_path = az_path

    def get_azure_access_token(self):
        """
        Synchronously fetches a new Azure access token using the Azure CLI.
        """
        try:
            logging.info("Fetching Azure OpenAI access token...")
            result = subprocess.run(
                [
                    self.az_path, 'account', 'get-access-token',
                    '--resource', 'https://cognitiveservices.azure.com',
                    '--query', 'accessToken', '-o', 'tsv'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                logging.error(f"Failed to fetch access token: {result.stderr.decode('utf-8')}")
                return None
            return result.stdout.decode('utf-8').strip()
        except Exception as e:
            logging.error(f"Error fetching access token: {e}")
            return None

    async def refresh_token(self):
        """
        Asynchronously refreshes the Azure access token.
        """
        async with self.token_lock:  # Correct usage with asyncio.Lock
            if self.refresh_in_progress.is_set():
                logging.info("Token refresh already in progress. Waiting...")
                await self.refresh_in_progress.wait()
                return

            self.refresh_in_progress.set()
            try:
                logging.info("Refreshing Azure access token...")
                new_token = self.get_azure_access_token()
                if new_token:
                    self.access_token = new_token
                    # Set token to expire in 25 minutes (1500 seconds)
                    self.token_expiry_time = time.time() + 1500
                    os.environ['AZURE_OPENAI_API_KEY'] = self.access_token
                    logging.info("Token refreshed successfully.")
                else:
                    logging.error("Failed to refresh Azure access token.")
            finally:
                self.refresh_in_progress.clear()

    async def ensure_valid_token(self):
        """
        Ensures that the Azure access token is valid and refreshes it if necessary.
        """
        if self.access_token is None or time.time() > self.token_expiry_time - 300:
            logging.info("Access token is expired or about to expire. Triggering refresh...")
            await self.refresh_token()

# Instantiate a global TokenManager
token_manager = TokenManager()

async def get_or_refresh_token():
    """
    Public function to get or refresh the Azure access token.
    """
    await token_manager.ensure_valid_token()
    return token_manager.access_token
