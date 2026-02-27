import boto3
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Setup Resource
dynamodb = boto3.resource('dynamodb', 
                          aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
                          aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
                          region_name=os.getenv("AWS_REGION", "us-east-2"))

def reset_database():
    table_names = ['Users', 'PhotoGallery']
    
    for name in table_names:
        try:
            table = dynamodb.Table(name)
            print(f"Deleting table: {name}...")
            table.delete()
            # Wait for deletion to finish
            table.meta.client.get_waiter('table_not_exists').wait(TableName=name)
            print(f"Successfully deleted {name}.")
        except Exception as e:
            print(f"Table {name} did not exist or could not be deleted: {e}")

    print("\n--- Starting Recreation ---\n")

    # 1. Create Users Table
    # Note: Username MUST be the Partition Key for your app logic to work
    print("Creating Users table...")
    dynamodb.create_table(
        TableName='Users',
        KeySchema=[{'AttributeName': 'Username', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'Username', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # 2. Create PhotoGallery Table
    print("Creating PhotoGallery table...")
    dynamodb.create_table(
        TableName='PhotoGallery',
        KeySchema=[{'AttributeName': 'PhotoID', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'PhotoID', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    print("Waiting for tables to become ACTIVE...")
    # Wait for the tables to be ready before finishing
    for name in table_names:
        dynamodb.meta.client.get_waiter('table_exists').wait(TableName=name)
        print(f"Table {name} is now ACTIVE and ready for use.")

if __name__ == "__main__":
    reset_database()