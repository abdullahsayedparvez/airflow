import pymongo
from pymongo import MongoClient
from bson import Binary
from datetime import datetime
from io import BytesIO
import pandas as pd

# Connect to MongoDB (adjust your connection string as needed)
client = MongoClient("mongodb://localhost:27017/")
db = client['data']
collection = db['prices_data']
current_time = datetime.now()
excel_file_name = rf'tatasteel.xlsx'
# Open the Excel file in binary mode
# with open(rf'/home/abdullah/airflowpractise/data/raw/{excel_file_name}', 'rb') as f:
#     file_data = f.read()

# # Store the binary data into MongoDB
# file_doc = {
#     'filename': 'tatasteel.xlsx',
#     'data': Binary(file_data),
#     'upload_time': current_time  # Adding the timestamp
# }


# # Insert the file document into the collection
# collection.insert_one(file_doc)
# print("File stored successfully in MongoDB!")


############## read the document  ##################

file_doc = collection.find_one({'filename': 'tatasteel.xlsx'})

# Extract the binary data
file_data = file_doc['data']

# Use BytesIO to convert the binary data into a file-like object
file_like_object = BytesIO(file_data)

# Read the Excel data into a pandas DataFrame
df = pd.read_excel(file_like_object)

# Now you can work with the DataFrame
print(df.head())  # Display the first few rows of the DataFrame