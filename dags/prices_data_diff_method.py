from airflow.decorators import dag, task
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
MONGODB_DATABASE = os.getenv("MONGODB_DAATBASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")

TICKER = "TATASTEEL.NS"
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
    dag_id="prices_dag_taskflow",
    default_args=default_args,
    description="Fetch and store Tata Steel data using TaskFlow API",
    schedule_interval=None,
    start_date=datetime(2025, 4, 20),
    catchup=False,
    tags=["yfinance", "tatasteel"],
)
def prices_pipeline():

    @task
    def fetch_data():
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=365)

        df = yf.download(TICKER, start=start_date, end=end_date, group_by="ticker")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(1)

        df.reset_index(inplace=True)
        return df.to_json(date_format="iso")


    @task
    def clean_data(raw_json: str):
        df = pd.read_json(raw_json)
        df["Ticker"] = TICKER
        df = df[["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]]
        return df.to_json(date_format="iso")


    @task
    def save_to_excel(clean_json: str):
        df = pd.read_json(clean_json)
        file_path = os.path.join(RAW_DIR, "tatasteel.xlsx")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_excel(file_path, index=False)
        save_to_mongo(file_path)


    def save_to_mongo(file_path):
        with open(file_path, 'rb') as f:
            file_data = f.read()

        current_time = datetime.now()
        file_doc = {
            'filename': os.path.basename(file_path),
            'data': Binary(file_data),
            'upload_time': current_time
        }

        collection.insert_one(file_doc)
        print(f"File {os.path.basename(file_path)} stored in MongoDB!")

    # Task chaining
    raw_data = fetch_data()
    cleaned_data = clean_data(raw_data)
    save_to_excel(cleaned_data)

dag = prices_pipeline()
