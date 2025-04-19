from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import pendulum

# Set timezone to IST
local_tz = pendulum.timezone("Asia/Kolkata")

# Define the function that will be executed by the task
def print_hello():
    print("Hello, World!")

# Define the DAG
dag = DAG(
    'hello_world_dag',  # The DAG name
    description='A simple Hello World DAG',
    schedule_interval='15 17 * * *',  # Runs at 4:15 PM IST daily
    start_date=pendulum.datetime(2025, 4, 18, 0, 0, tz="Asia/Kolkata"),  # Use India time here
    catchup=False,
)

# Define the task
hello_task = PythonOperator(
    task_id='print_hello_task',
    python_callable=print_hello,
    dag=dag,
)

hello_task
