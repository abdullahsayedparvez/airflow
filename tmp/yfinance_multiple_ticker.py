from airflow.decorators import dag, task
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from pymongo import MongoClient 
from bson import Binary 


TICKER_LIST = ["TATASTEEL","TCS"]


def fetch_data(TICKER):
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=365)

    df = yf.download(TICKER, start=start_date, end=end_date, group_by="ticker")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)

    df.reset_index(inplace=True)
    print(df)
    return df.to_json(date_format="iso")

# for ticker in TICKER_LIST:
#     print(fetch_data(ticker))
end_date = datetime.today().date()
start_date = end_date - timedelta(days=10)

df = yf.download('TATASTEEL.NS', start=start_date, end=end_date, group_by="ticker")
print(df)

