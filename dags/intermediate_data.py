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
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
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


def store_df_in_mysql(df: pd.DataFrame, TICKER: str):
    """Create DB if needed, use it, and store the DataFrame into MySQL."""
    try:
        # Single connection — no DB selected yet
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=int(MYSQL_PORT),
            user=MYSQL_USERNAME,
            password=MYSQL_PASSWORD
        )

        with connection.cursor() as cursor:
            # 1️⃣ Ensure database exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}`;")
            connection.commit()
            print(f"✅ Database `{MYSQL_DATABASE}` ensured.")

            # 2️⃣ Use the database
            cursor.execute(f"USE `{MYSQL_DATABASE}`;")

            # 3️⃣ Drop and create the table
            cursor.execute(f"DROP TABLE IF EXISTS `{TICKER}`;")
            create_table_query = f"""
                CREATE TABLE `{TICKER}` (
                    Ticker VARCHAR(50),
                    Date DATE,
                    Open FLOAT,
                    High FLOAT,
                    Low FLOAT,
                    Close FLOAT,
                    Volume BIGINT,
                    RSI FLOAT
                );
            """
            cursor.execute(create_table_query)

            # 4️⃣ Clean NaNs
            df.fillna(0, inplace=True)

            # 5️⃣ Insert rows
            insert_query = f"""
                INSERT INTO `{TICKER}` (Ticker, Date, Open, High, Low, Close, Volume, RSI)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            for _, row in df.iterrows():
                cursor.execute(insert_query, (
                    row["Ticker"],
                    row["Date"],
                    row["Open"],
                    row["High"],
                    row["Low"],
                    row["Close"],
                    row["Volume"],
                    row["RSI"]
                ))

            connection.commit()
            print("✅ Data inserted into MySQL successfully.")

        connection.close()

    except Exception as e:
        print("❌ MySQL Insert Error:", e)



@dag(
    dag_id="ticker_insicator_downloader",
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
        TICKER = file_doc["ticker"]
        df = pd.read_excel(io.BytesIO(file_binary))
        print("DataFrame Loaded: ")
        print(df)

        return {
        "df": df.to_json(date_format='iso'),
        "ticker": TICKER
        }

    @task()
    def calculate_rsi_task(data:dict):
        """Calculate the RSI and return the modified DataFrame."""
        df = pd.read_json(data["df"])
        df['RSI'] = calculate_rsi(df)
        print("RSI Calculated:")
        print(df[['Date', 'Close', 'RSI']])  

        return {
        "df": df.to_json(date_format='iso'),
        "ticker": data["ticker"]
            }

    @task()
    def save_to_excel_to_local(data: dict):
        """Save the DataFrame to an Excel file locally."""
        df = pd.read_json(data["df"])
        ticker = data["ticker"]
        file_path = os.path.join(RAW_DIR, f"{ticker}.xlsx")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_excel(file_path, index=False)
        print(f"File saved to {file_path}")
        return data

    @task()
    def store_in_mysql_task(data: dict):
        df = pd.read_json(data["df"])
        ticker = data["ticker"]
        store_df_in_mysql(df, ticker)
    

    data = fetch_excel_from_mongo()
    data_with_rsi = calculate_rsi_task(data)
    data_saved = save_to_excel_to_local(data_with_rsi)
    store_in_mysql_task(data_saved)

dag_instance = read_excel_from_mongo_with_rsi()