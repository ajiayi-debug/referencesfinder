from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ServerSelectionTimeoutError
import certifi
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Replace with your actual MongoDB URI
mongo_uri = os.getenv('uri_mongo')

try:
    # Create a MongoClient with TLS/SSL verification
    client = MongoClient(
        mongo_uri,
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA bundle for certificate verification
    )

    # Attempt to list databases to test the connection
    databases = client.list_database_names()
    print("SSL certificate verification succeeded. Connection to MongoDB established.")
    print("Databases available:", databases)

except (ConfigurationError, ServerSelectionTimeoutError) as config_error:
    print(f"Configuration or server selection error occurred: {config_error}")
except Exception as e:
    print(f"An error occurred: {e}")