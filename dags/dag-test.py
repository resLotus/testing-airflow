from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta
import pandas as pd
import psycopg2

default_args = {
  'owner': 'try',
  'retries': 5,
  'retry_delay': timedelta(minutes=2)
}

@dag(
  dag_id='01_dag_test',
  description='first dag',
  start_date=datetime(2022, 7, 29, 2),
  schedule_interval='@daily'
)
def dag_test():
    source_path = r'./dags/data_input/deniro.csv'
    input_values_path = r'./dags/data_input/input_values.csv'
    year_value_path = r'./dags/data_output/deniro_year_value.csv'
    year_column_path = r'./dags/data_output/deniro_year_column.csv'
    variable_filter_path = r'./dags/data_output/deniro_variable_filter.csv'

    @task(task_id='read_input_values')
    def read_input_values(ti=None):
        input_values = pd.read_csv(input_values_path, delimiter=';')
        print(input_values)
        ti.xcom_push("year_filter", input_values.iloc[0]["Value"])
        ti.xcom_push("column_filter", input_values.iloc[1]["Value"])

    @task(task_id='filter_by_year_value')
    def filter_by_year_value(ti=None):
        year_filter = int(ti.xcom_pull(task_ids="read_input_values", key="year_filter"))
        movies = pd.read_csv(source_path)
        filtered = movies[movies["Year"] > year_filter]
        filtered.to_csv(year_value_path)

    @task(task_id='filter_by_year_column')
    def filter_by_year_column(ti=None):
        column_filter = ti.xcom_pull(task_ids="read_input_values", key="column_filter").split(',')
        movies = pd.read_csv(source_path)
        filtered = movies.filter(items=column_filter)
        filtered.to_csv(year_column_path)

    @task(task_id='filter_using_variable')
    def filter_using_variable(ti=None):
        column_filter = Variable.get("column_filter").split(',')
        movies = pd.read_csv(source_path)
        filtered = movies.filter(items=column_filter)
        filtered.to_csv(variable_filter_path)

    @task(task_id='connect_to_db')
    def connect_to_db(ti=None):
        DB_NAME = ""
        DB_USER = "airflow"
        DB_PASS = "airflow"
        DB_HOST = "postgres"
        DB_PORT = "5432"

        conn = psycopg2.connect(database=DB_NAME,
                                user=DB_USER,
                                password=DB_PASS,
                                host=DB_HOST,
                                port=DB_PORT)

        cur = conn.cursor()
        cur.execute("SELECT * FROM pg_catalog.pg_tables")

        rows = cur.fetchall()
        for data in rows:
            print("ID :" + str(data[0]))
            print("NAME :" + data[1])

    read_from_db = PostgresOperator(postgres_conn_id="postgres", task_id="read_from_db", sql="SELECT * FROM pg_catalog.pg_tables;")

    read_input_values() >> [filter_by_year_value(), filter_by_year_column()]
    filter_using_variable() >> read_from_db
    connect_to_db()


dag_test()
