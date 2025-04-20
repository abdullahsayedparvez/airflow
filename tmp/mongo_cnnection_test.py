from pymongo import MongoClient

# Connect to the MongoDB server (default: localhost:27017)
client = MongoClient("mongodb://localhost:27017/")

# Access a specific database
db = client["prices_data"]

# Access a collection within the database
collection = db["prices_data"]

# Example operation: insert a document
collection.insert_one({"name": "Alice", "age": 30})

# Example operation: find a document
result = collection.find_one({"name": "Alice"})
print(result)