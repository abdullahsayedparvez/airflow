from airflow.decorators import dag, task, task_group
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from pymongo import MongoClient 
from bson import Binary 

# Load .env variables
load_dotenv()

DATA_DIR = os.getenv("DATA_DIR")
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Abdullah@123")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "airflow")

RAW_DIR = os.path.join(DATA_DIR, "intermediate/rsi")

# TICKER = "TATASTEEL.NS"
TICKER_LIST = ["TATASTEEL.NS","TCS.NS"]
RAW_DIR = os.path.join(DATA_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

client = MongoClient(MONGODB_HOST)
db = client[MONGODB_DATABASE]
collection = db[MONGODB_COLLECTION]

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

@dag(
    dag_id="raw_prices_data_downloader",
    default_args=default_args,
    description="Fetch and store Tata Steel data using TaskFlow API",
    schedule_interval=None,
    start_date=datetime(2025, 4, 20),
    catchup=False,
    tags=["yfinance", "tatasteel"],
)
def prices_pipeline():

    # @task
    # def fetch_data(ticker):
    #     end_date = datetime.today().date()
    #     start_date = end_date - timedelta(days=365)

    #     df = yf.download(ticker, start=start_date, end=end_date, group_by="ticker")

    #     if isinstance(df.columns, pd.MultiIndex):
    #         df.columns = df.columns.get_level_values(1)

    #     df.reset_index(inplace=True)
    #     return df.to_json(date_format="iso")
    

    @task
    def fetch_data_testing(ticker):
        # Get the current date (ignoring time)
        current_date = datetime.today().date()

        # Check if a document with the given ticker exists and the upload_time matches today's date
        existing_doc = collection.find_one({'ticker': ticker})

        if existing_doc:
            # Extract the date part of 'upload_time'
            upload_date = existing_doc['upload_time'].date()

            # Check if the upload_time is from today
            if upload_date == current_date:
                print(f"Document for ticker {ticker} already exists with today's date!")
                return None  # Return the existing document or modify as needed

        # If the document doesn't exist or the date doesn't match, fetch the data
        end_date = current_date
        start_date = end_date - timedelta(days=365)

        # Fetch data from Yahoo Finance
        df = yf.download(ticker, start=start_date, end=end_date, group_by="ticker")

        # If the columns are multi-index, flatten them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(1)

        df.reset_index(inplace=True)

        # Return the data as a JSON string in ISO format
        return df.to_json(date_format="iso")


    @task
    def clean_data(raw_json: str,ticker):
        df = pd.read_json(raw_json)
        df["Ticker"] = ticker
        df = df[["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]]
        return df.to_json(date_format="iso")


    @task
    def save_to_excel(clean_json: str,ticker):
        df = pd.read_json(clean_json)
        file_path = os.path.join(RAW_DIR, f"{ticker}.xlsx")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_excel(file_path, index=False)
        save_to_mongo(file_path,ticker)


    def save_to_mongo(file_path,ticker):
        with open(file_path, 'rb') as f:
            file_data = f.read()

        current_time = datetime.now()
        file_doc = {
            'ticker': ticker,
            'filename': os.path.basename(file_path),
            'data': Binary(file_data),
            'upload_time': current_time
        }

        collection.insert_one(file_doc)
        print(f"File {os.path.basename(file_path)} stored in MongoDB!")


    # Using Task Group to handle each ticker separately
        

    for ticker in TICKER_LIST:
        raw_data = fetch_data_testing(ticker)
        if not raw_data:
            print(f"Today's data for {ticker} is already in MongoDB, skipping...")
            continue
        cleaned_data = clean_data(raw_data, ticker)
        save_to_excel(cleaned_data, ticker)

dag = prices_pipeline()
