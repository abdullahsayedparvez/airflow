from airflow.decorators import dag, task
from datetime import datetime, timedelta
import pandas as pd
import io
from dotenv import load_dotenv
from pymongo import MongoClient
import os
import pymysql
from sqlalchemy import create_engine
load_dotenv()


MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DAATBASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Abdullah@123")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "airflow")
DATA_DIR = os.getenv("DATA_DIR")
RAW_DIR = os.path.join(DATA_DIR, "intermediate/rsi")
os.makedirs(RAW_DIR, exist_ok=True)


default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def calculate_rsi(df, window=14):
    """Calculate the Relative Strength Index (RSI) for a given DataFrame."""
    delta = df['Close'].diff()  
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()  
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()  
    
    rs = gain / loss 
    rsi = 100 - (100 / (1 + rs))  
    
    return rsi


def store_df_in_mysql(df):
    """Store DataFrame into MySQL database."""
    # Create SQLAlchemy engine to connect to MySQL
    engine = create_engine(f'mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}')
    
    # Insert the DataFrame into a table (e.g., 'stock_data')
    df.to_sql('stock_data', con=engine, if_exists='replace', index=False)  # 'replace' will drop the table if it exists


@dag(
    dag_id="read_excel_from_mongo_dag_with_rsi",
    default_args=default_args,
    description="Fetch Excel file from MongoDB and calculate RSI as a separate task",
    schedule_interval=None, 
    start_date=datetime(2025, 4, 22),
    catchup=False,
    tags=["mongodb", "excel", "rsi"],
)
def read_excel_from_mongo_with_rsi():

    @task()
    def fetch_excel_from_mongo():
        """Fetch the Excel file from MongoDB."""
        client = MongoClient(MONGODB_HOST)
        db = client[MONGODB_DATABASE]
        collection = db[MONGODB_COLLECTION]
        file_doc = collection.find_one(sort=[("upload_time", -1)])
        file_binary = file_doc["data"]
        df = pd.read_excel(io.BytesIO(file_binary))
        print("DataFrame Loaded: ")
        print(df)

        return df  

    @task()
    def calculate_rsi_task(df: pd.DataFrame):
        """Calculate the RSI and return the modified DataFrame."""
        df['RSI'] = calculate_rsi(df)
        print("RSI Calculated:")
        print(df[['Date', 'Close', 'RSI']])  

        return df  

    @task()
    def save_to_excel_to_local(df: pd.DataFrame):
        """Save the DataFrame to an Excel file locally."""
        file_path = os.path.join(RAW_DIR, "tatasteel.xlsx")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_excel(file_path, index=False)
        print(f"File saved to {file_path}")
        return df

    @task()
    def store_in_mysql_task(df: pd.DataFrame):
        """Store the DataFrame in MySQL database."""
        store_df_in_mysql(df)
        print("DataFrame stored in MySQL successfully.")
    

    df = fetch_excel_from_mongo() 
    df_with_rsi = calculate_rsi_task(df)  
    save_local = save_to_excel_to_local(df_with_rsi)  
    store_in_mysql_task(df)

dag_instance = read_excel_from_mongo_with_rsi()