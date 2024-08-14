from pymongo import UpdateOne, MongoClient

def upsert_database_and_collection(uri, db_name, collection_name, records):
    """
    Insert a whole collection into a database if it doesn't exist,
    or update the collection if it does.

    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        collection_name (str): Name of the collection.
        records (list): List of dictionaries to be inserted or updated.
    """
    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]

    # Check if the collection exists
    existing_collections = client[db_name].list_collection_names()
    collection_exists = collection_name in existing_collections

    if not collection_exists:
        # Collection doesn't exist, insert all records
        if records:
            collection.insert_many(records)
            print(f"Inserted {len(records)} records into {collection_name}.")
    else:
        # Collection exists, update existing records
        operations = []
        for record in records:
            query = {"PDF File": record["PDF File"]}
            update = {"$set": record}
            operations.append(UpdateOne(query, update, upsert=True))
        
        result = collection.bulk_write(operations)
        print(f"Matched: {result.matched_count}, Modified: {result.modified_count}, Upserts: {result.upserted_count}")






def replace_database_collection(uri, db_name, collection_name, records):
    """
    Replace the entire collection in the database with the new records.
    
    Args:
        uri (str): MongoDB connection URI.
        db_name (str): Name of the database.
        collection_name (str): Name of the collection.
        records (list): List of dictionaries to be inserted.
    """
    client = MongoClient(uri)
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