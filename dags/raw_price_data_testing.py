from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import Binary

# Load environment variables
load_dotenv()

# Constants
DATA_DIR = os.getenv("DATA_DIR")
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")

TICKER_LIST = ["TATASTEEL.NS", "TCS.NS"]
RAW_DIR = os.path.join(DATA_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# MongoDB setup
client = MongoClient(MONGODB_HOST)
db = client[MONGODB_DATABASE]
collection = db[MONGODB_COLLECTION]

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

@dag(
    dag_id="raw_prices_data_downloader_branching",
    default_args=default_args,
    schedule_interval=None,
    start_date=datetime(2025, 4, 20),
    catchup=False,
    tags=["yfinance", "branching", "mongo"],
)
def prices_pipeline():

    def save_to_mongo(file_path, ticker):
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
        print(f"✅ Stored {ticker} in MongoDB: {file_path}")


    def create_ticker_pipeline(ticker: str):
        @task(task_id=f"fetch_data_{ticker}")
        def fetch_data(ticker):
            current_date = datetime.utcnow().date()
            end_date = current_date
            start_date = end_date - timedelta(days=365)
            df = yf.download(ticker, start=start_date, end=end_date, group_by="ticker")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(1)
            df.reset_index(inplace=True)
            return df.to_json(date_format="iso")

        @task(task_id=f"clean_data_{ticker}")
        def clean_data(raw_json: str,ticker:str):
            df = pd.read_json(raw_json)
            df["Ticker"] = ticker
            df = df[["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]]
            return df.to_json(date_format="iso")

        @task(task_id=f"save_to_excel_{ticker}")
        def save_to_excel(clean_json: str,ticker:str):
            df = pd.read_json(clean_json)
            file_path = os.path.join(RAW_DIR, f"{ticker}.xlsx")
            df.to_excel(file_path, index=False)
            save_to_mongo(file_path, ticker)

        def branch_condition(ticker):
            current_date = datetime.utcnow().date()
            existing_doc = collection.find_one({'ticker': ticker})
            if existing_doc and existing_doc['upload_time'].date() == current_date:
                print(f"⏭️ Skipping {ticker}: Data already exists in MongoDB for today.")
                return f"skip_task_{ticker}"
            else:
                print(f"✅ Proceeding with {ticker}: Data needs update.")
                return f"fetch_data_{ticker}"


        # creating empty task skip_task_ and end_
        skip_task = EmptyOperator(task_id=f"skip_task_{ticker}")   
        end = EmptyOperator(task_id=f"end_{ticker}")               

        # Other user build task 
        fetched = fetch_data(ticker)
        cleaned = clean_data(fetched, ticker)
        saved = save_to_excel(cleaned, ticker)


        # Task id for the task exceution will be initialize from branch condition
        branch = BranchPythonOperator(
            task_id=f"branch_{ticker}",
            python_callable=lambda: branch_condition(ticker),  # here we will get either skip_task_{ticker} or fetch_data_{ticker}
        )
        # routing task 
        branch >> [fetched, skip_task]
        fetched >> cleaned >> saved >> end
        skip_task >> end
    
    for ticker in TICKER_LIST:
        create_ticker_pipeline(ticker)

dag = prices_pipeline()
