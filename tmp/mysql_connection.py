from sqlalchemy import create_engine
import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# load_dotenv()
print(f"MONGODB_HOST: {os.getenv('MONGODB_HOST')}")

# # MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
# MYSQL_HOST = 'localhost'
# MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
# MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
# MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Abdullah@123")
# MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "intermediate")

# try:
#     connection = pymysql.connect(
#         host=MYSQL_HOST,
#         port=MYSQL_PORT,
#         user=MYSQL_USERNAME,
#         password=MYSQL_PASSWORD,
#         database=MYSQL_DATABASE
#     )

#     with connection.cursor() as cursor:
#         cursor.execute("SELECT VERSION();")
#         version = cursor.fetchone()
#         print(f"✅ Connected to MySQL! Server version: {version[0]}")

#     connection.close()

# except Exception as e:
#     print("❌ Failed to connect to MySQL")
#     print(e)
