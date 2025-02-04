from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import os
from datetime import datetime

# Define o diretório base e cria um subdiretório por data de execução
BASE_DIR = '/opt/airflow/data/extract/'
DATE_DIR = datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR = os.path.join(BASE_DIR, DATE_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_postgres_tables():
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')  # Conexão com o banco principal
    tables = [
        'categories', 'customer_customer_demo', 'customer_demographics', 'customers', 'employees',
        'employee_territories', 'orders', 'products', 'region', 'shippers', 'suppliers', 'territories', 'us_states'
    ]
    
    for table in tables:
        df = pg_hook.get_pandas_df(f'SELECT * FROM {table}')
        df.to_csv(os.path.join(OUTPUT_DIR, f'{table}.csv'), index=False)

def process_order_details():
    input_path = '/opt/airflow/data/order_details.csv'  # Caminho de entrada permanece o mesmo
    df = pd.read_csv(input_path)
    
    # Salva a saída na mesma pasta dos outros arquivos extraídos
    df.to_csv(os.path.join(OUTPUT_DIR, 'order_details.csv'), index=False)

def load_data_to_postgres_second():
    # Conectando ao banco de dados secundário
    pg_hook = PostgresHook(postgres_conn_id='postgres_second')  # Conexão com o banco secundário
    tables = [
        'categories', 'customer_customer_demo', 'customer_demographics', 'customers', 'employees',
        'employee_territories', 'orders', 'products', 'region', 'shippers', 'suppliers', 'territories', 'us_states',
        'order_details'
    ]
    
    for table in tables:
        file_path = os.path.join(OUTPUT_DIR, f'{table}.csv')
        df = pd.read_csv(file_path)
        df.to_sql(table, pg_hook.get_sqlalchemy_engine(), if_exists='replace', index=False)

with DAG(
    'etl_airflow_postgres',
    start_date=datetime(2025, 2, 2),
    schedule_interval='@daily',
    catchup=False
) as dag:
    
    extract_task = PythonOperator(
        task_id='extract_postgres_tables',
        python_callable=extract_postgres_tables
    )
    
    process_csv_task = PythonOperator(
        task_id='process_order_details',
        python_callable=process_order_details
    )
    
    load_task = PythonOperator(
        task_id='load_data_to_postgres_second',
        python_callable=load_data_to_postgres_second
    )
    
    extract_task >> process_csv_task >> load_task
