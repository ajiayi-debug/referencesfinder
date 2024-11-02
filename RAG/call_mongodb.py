from pymongo import UpdateOne, MongoClient
import certifi


def upsert_database_and_collection(uri, db_name, collection_name, records,key):
    """
    Insert records into a MongoDB collection if they don't exist,
    or update the records if they do, using the '_id' field when present.

    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        collection_name (str): Name of the collection.
        records (list): List of dictionaries to be inserted or updated.
    """
    from pymongo.errors import BulkWriteError

    if not isinstance(records, list):
        raise TypeError("Records must be a list of dictionaries.")

    client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
    db = client[db_name]
    collection = db[collection_name]

    try:
        # Prepare bulk operations
        operations = []
        for record in records:
            if not isinstance(record, dict):
                raise TypeError(f"Each record must be a dictionary. Found: {type(record)}")

            if '_id' in record:
                # Use '_id' field for upsert
                query = {'_id': record['_id']}
                update = {"$set": record}
                operations.append(UpdateOne(query, update, upsert=True))
            else:
                # Insert as a new document if no '_id' field
                operations.append(UpdateOne(record, {"$setOnInsert": record}, upsert=True))

        if operations:
            result = collection.bulk_write(operations)
            print(f"Bulk write completed: Matched {result.matched_count}, Modified {result.modified_count}, Upserted {len(result.upserted_ids)} documents.")
        else:
            print("No operations to perform.")

    except BulkWriteError as bwe:
        print("Bulk write error occurred:", bwe.details)
    except Exception as e:
        print("An error occurred:", str(e))
    finally:
        client.close()





def replace_database_collection(uri, db_name, collection_name, records):
    """
    Replace the entire collection in the database with the new records.
    
    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        collection_name (str): Name of the collection.
        records (list): List of dictionaries to be inserted.
    """
    client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
    db = client[db_name]
    collection = db[collection_name]

    # Drop the existing collection if it exists
    if collection_name in db.list_collection_names():
        db.drop_collection(collection_name)
        print(f"Dropped existing collection: {collection_name}")

    # Insert all records into the new collection
    if records:
        collection.insert_many(records)
        print(f"Inserted {len(records)} records into {collection_name}.")

#for agentic search
def add_prompt_to_db(uri, db_name, collection_name, prompt):
    """
    Adds a prompt to the MongoDB database if it doesn't already exist.

    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        collection_name (str): Name of the collection.
        prompt (str): The prompt to be added.
    """
    client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
    db = client[db_name]
    collection = db[collection_name]

    # Upsert operation
    result = collection.update_one(
        {'prompt': prompt},      # Query: look for a document with this prompt
        {'$setOnInsert': {'prompt': prompt}},  # Only set if it's a new document
        upsert=True
    )

    if result.matched_count == 0 and result.upserted_id is not None:
        print("Prompt added to the database.")
    else:
        print("Prompt already exists in the database.")

#duplicate a collection
def duplicate_collection(uri, db_name, source_collection_name, target_collection_name):
    """
    Duplicate a collection in MongoDB.

    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        source_collection_name (str): Name of the source collection to duplicate.
        target_collection_name (str): Name of the target collection where data will be copied.
    """
    # Establish a secure connection to MongoDB
    client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
    db = client[db_name]
    
    source_collection = db[source_collection_name]
    target_collection = db[target_collection_name]

    # Check if the target collection already exists
    if target_collection_name in db.list_collection_names():
        print(f"The target collection '{target_collection_name}' already exists.")
        # Optionally, you can drop the target collection if you want to overwrite it
        # db.drop_collection(target_collection_name)
        # print(f"Dropped existing collection '{target_collection_name}'.")
        # target_collection = db[target_collection_name]
    else:
        print(f"Creating target collection '{target_collection_name}'.")

    # Fetch all documents from the source collection
    documents = list(source_collection.find())
    print(f"Fetched {len(documents)} documents from '{source_collection_name}'.")

    if documents:
        # Insert documents into the target collection
        target_collection.insert_many(documents)
        print(f"Inserted {len(documents)} documents into '{target_collection_name}'.")
    else:
        print(f"No documents found in '{source_collection_name}' to duplicate.")

    # Close the connection
    client.close()

#function to delete for agentic rag test. ONLY FOR THAT very specific test so yeah
def delete_documents_by_reference_text(uri, db_name, collection_name, reference_text):
    """
    Delete documents from a MongoDB collection where 'Reference text in main article' matches the given value.

    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        collection_name (str): Name of the collection.
        reference_text (str): The value of 'Reference text in main article' to match for deletion.
    """
    # Establish a secure connection to MongoDB
    client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
    db = client[db_name]
    collection = db[collection_name]

    # Define the query to match documents
    query = {'Reference text in main article': reference_text}

    # Count the number of documents to be deleted
    count = collection.count_documents(query)
    if count == 0:
        print(f"No documents found with 'Reference text in main article' = '{reference_text}'.")
    else:
        print(f"Found {count} document(s) to delete.")

        # Delete the documents
        result = collection.delete_many(query)
        print(f"Deleted {result.deleted_count} document(s) from '{collection_name}'.")

    # Close the connection
    client.close()



#insert documents blindly (no key)
def insert_documents(uri, db_name, collection_name, records):
    """
    Insert records into a MongoDB collection without upserting.

    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        collection_name (str): Name of the collection.
        records (list): List of dictionaries to be inserted.
    """
    from pymongo.errors import BulkWriteError

    if not isinstance(records, list):
        raise TypeError("Records must be a list of dictionaries.")

    client = MongoClient(uri, tls=True, tlsCAFile=certifi.where())
    db = client[db_name]
    collection = db[collection_name]

    try:
        if records:
            # Remove '_id' fields to avoid duplicate key errors
            for record in records:
                record.pop('_id', None)

            result = collection.insert_many(records, ordered=False)
            print(f"Inserted {len(result.inserted_ids)} records into '{collection_name}'.")
        else:
            print("No records to insert.")

    except BulkWriteError as bwe:
        print("Bulk write error occurred:", bwe.details)
    except Exception as e:
        print("An error occurred:", str(e))
    finally:
        client.close()

