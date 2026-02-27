import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Use the same credentials as your app
dynamodb = boto3.resource('dynamodb', 
                          aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
                          aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
                          region_name=os.getenv("AWS_REGION", "us-east-2"))

def create_tables():
    # 1. Create Users Table
    print("Creating Users table...")
    dynamodb.create_table(
        TableName='Users',
        KeySchema=[{'AttributeName': 'Username', 'KeyType': 'HASH'}], # Partition key
        AttributeDefinitions=[{'AttributeName': 'Username', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )

    # 2. Create PhotoGallery Table
    print("Creating PhotoGallery table...")
    dynamodb.create_table(
        TableName='PhotoGallery',
        KeySchema=[{'AttributeName': 'PhotoID', 'KeyType': 'HASH'}], # Partition key
        AttributeDefinitions=[{'AttributeName': 'PhotoID', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    print("Tables are being created. This may take a minute!")

if __name__ == "__main__":
    create_tables()