from pathlib import Path
import os
import re
import json
import logging

import pandas as pd
import sqlalchemy as sa

from .sql_processor import SQLProcessor
from sqlalchemy.exc import ResourceClosedError

sql_processor = SQLProcessor()


def load_data_from_bd(config: dict,
                      name_sql_file: str,
                      base_dir,
                      schema,
                      table_name,
                      params_names: object = None,
                      params_values: object = None,
                      name_sql_dir: str = 'sql_query_files',
                      expanding: bool = True) -> pd.DataFrame:
    try:
        print(f'->Выполняем подключение к бд и выгрузку из таблицы - {schema}.{table_name} <-')
        sql_processor.extract_settings_url = (
            f'{config["psql_conn_type"]}ql+psycopg2://'
            f'{config["psql_login"]}:{config["psql_password"]}'
            f'@{config["psql_hostname"]}:{config["psql_port"]}'
            f'/{config["psql_name_bd"]}'
        )

        extract_query = sql_processor.get_query_from_sql_file(
            name_sql_file,
            base_dir,
            query_dir=name_sql_dir,
            params_names=params_names,
            params_values=params_values,
            expanding=expanding,
        )

        sql_processor.create_extract_engine()

        with sql_processor.extract_settings_connect() as connection:
            try:
                data = sql_processor.extract_data_sql(
                    extract_query,
                    connection=connection,
                    params=params_values,
                )
                print(f'->Выгрузка из таблицы - {schema}.{table_name} - успешна <-')
                return data

            except ResourceClosedError:
                connection.detach()
                print(f'->Выгрузка из таблицы - {schema}.{table_name} - успешна <-')
                return True

    except Exception as e:
        print(f'->Ошибка {e} при выгрузке данных из таблицы - {schema}.{table_name} <-')
        raise e