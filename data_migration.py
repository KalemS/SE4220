import boto3
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# AWS Setup
dynamodb = boto3.resource('dynamodb', 
                          aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
                          aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
                          region_name=os.getenv("AWS_REGION", "us-east-2"))

# MongoDB Setup
mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client['CloudGalleryDB']

def migrate_data():
    tables = ['Users', 'PhotoGallery']
    
    for table_name in tables:
        print(f"Migrating {table_name}...")
        dy_table = dynamodb.Table(table_name)
        mg_collection = db[table_name]
        
        # Scan DynamoDB
        response = dy_table.scan()
        items = response.get('Items', [])
        
        if items:
            # Insert into MongoDB
            mg_collection.insert_many(items)
            print(f"Successfully migrated {len(items)} items to MongoDB collection: {table_name}")
        else:
            print(f"No data found in DynamoDB table: {table_name}")

if __name__ == "__main__":
    migrate_data()