from airflow.decorators import dag, task
from datetime import datetime, timedelta
import pandas as pd
import os
import io
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.binary import Binary

# Load environment variables
load_dotenv()

# MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_HOST = os.getenv("mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DAATBASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")

# Connect to MongoDB
client = MongoClient(MONGODB_HOST)
db = client[MONGODB_DATABASE]
collection = db[MONGODB_COLLECTION]

file_doc = collection.find_one(sort=[("upload_time", -1)])
excel_binary = file_doc["data"]
excel_file = io.BytesIO(excel_binary)
# Convert binary Excel to DataFrame
df = pd.read_excel(io.BytesIO(excel_file)) 
print(df)