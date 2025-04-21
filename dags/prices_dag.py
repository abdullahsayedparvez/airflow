from airflow import DAG
from airflow.operators.python import PythonOperator
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
MONGODB_DAATBASE = os.getenv("MONGODB_DAATBASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")
print(DATA_DIR)
TICKER = "TATASTEEL.NS"
RAW_DIR = os.path.join(DATA_DIR, "raw")

# Create base directory if not exists
os.makedirs(RAW_DIR, exist_ok=True)
client = MongoClient(MONGODB_HOST)
db = client[MONGODB_DAATBASE]
collection = db[MONGODB_COLLECTION]

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

# defining dags
with DAG(
    dag_id="prices_dag",
    default_args=default_args,
    description="Fetch and store Tata Steel data from yfinance",
    schedule_interval=None,
    start_date=datetime(2025, 4, 20),
    catchup=False,
    tags=["yfinance", "tatasteel"],
) as dag:
    
    # defining functions
    def fetch_data(**context):
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=365)

        df = yf.download(TICKER, start=start_date, end=end_date, group_by="ticker")
        
        # Handle multi-index columns if they appear
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(1)

        df.reset_index(inplace=True)
        context["ti"].xcom_push(key="raw_data", value=df.to_json(date_format="iso"))

    def clean_data(**context):
        raw_json = context["ti"].xcom_pull(key="raw_data")
        df = pd.read_json(raw_json)

        df["Ticker"] = TICKER
        df = df[["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]]

        context["ti"].xcom_push(key="clean_data", value=df.to_json(date_format="iso"))

    def save_to_excel(**context):
        clean_json = context["ti"].xcom_pull(key="clean_data")
        df = pd.read_json(clean_json)

        file_path = os.path.join(RAW_DIR, "tatasteel.xlsx")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_excel(file_path, index=False)

         # Call MongoDB to store the Excel file
        save_to_mongo(file_path)


    # Saving the Excel file to MongoDB as binary data
    def save_to_mongo(file_path):
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        current_time = datetime.now()

        # Prepare document to insert into MongoDB
        file_doc = {
            'filename': os.path.basename(file_path),
            'data': Binary(file_data),
            'upload_time': current_time
        }

        # Insert the file document into the collection
        print(MONGODB_COLLECTION)
        print(type(MONGODB_COLLECTION))
        collection = db[MONGODB_COLLECTION]
        print(f'mongodb host --> {MONGODB_HOST}')
        collection.insert_one(file_doc)
        
        print(f"File {os.path.basename(file_path)} stored successfully in MongoDB!")
    # defining tasks
    task_fetch_data = PythonOperator(
        task_id="fetch_data_from_yfinance",
        python_callable=fetch_data,
        provide_context=True
    )

    task_clean_data = PythonOperator(
        task_id="clean_yfinance_data",
        python_callable=clean_data,
        provide_context=True
    )

    task_save_data = PythonOperator(
        task_id="save_to_excel",
        python_callable=save_to_excel,
        provide_context=True
    )
    
    task_fetch_data >> task_clean_data >> task_save_data
