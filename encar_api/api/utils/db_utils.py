import logging

import pandas as pd
import sqlalchemy as sa

from .sql_processor import SQLProcessor
from sqlalchemy.exc import ResourceClosedError
from sqlalchemy import text

sql_processor = SQLProcessor()

logger = logging.getLogger('db_logger')


def load_data_from_bd(config: dict,
                      name_sql_file: str,
                      base_dir: str,
                      schema: str,
                      table_name: str,
                      params_names: object = None,
                      params_values: object = None,
                      name_sql_dir: str = 'sql_query_files',
                      expanding: bool = True) -> bool | pd.DataFrame:
    try:
        logger.info(f'->Выполняем подключение к бд и выгрузку из таблицы - {schema}.{table_name} <-')
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
                logger.info(f'->Выгрузка из таблицы - {schema}.{table_name} - успешна <-')
                return data

            except ResourceClosedError:
                connection.commit()
                connection.detach()
                logger.info(f'->Обновление таблицы - {schema}.{table_name} - успешно <-')
                return True

    except Exception as e:
        logger.error(f'->Ошибка {e} при выгрузке данных из таблицы - {schema}.{table_name} <-')
        raise e


def load_data_in_db(df: pd.DataFrame,
                    config: dict,
                    schema: str,
                    name_table_in_db: str,
                    exists='append',
                    index=False,
                    ):
    try:
        logger.info(f'->Вставляем записи в таблицу - {schema}.{name_table_in_db}  <-')

        load_settings_url = (
            f'{config["psql_conn_type"]}ql+psycopg2://'
            f'{config["psql_login"]}:{config["psql_password"]}'
            f'@{config["psql_hostname"]}:{config["psql_port"]}'
            f'/{config["psql_name_bd"]}'
        )

        engine = sa.create_engine(load_settings_url)
        with engine.connect() as connection:
            df.to_sql(
                name_table_in_db,
                con=connection,
                if_exists=exists,
                index=index,
                schema=schema
            )
            logger.info(f'->Записи в таблице - {schema}.{name_table_in_db} созданы <-')
            connection.detach()

    except Exception as e:
        logger.error(f'->Ошибка {e} при загрузке данных в таблицу - {schema}.{name_table_in_db} <-')
        raise e


def update_solo_data_in_db(config: dict,
                           name_sql_file: str,
                           base_dir: str,
                           schema: str,
                           table_name: str,
                           params_names: object = None,
                           params_values: object = None,
                           name_sql_dir: str = 'sql_query_files',
                           expanding: bool = True):
    try:
        logger.info(f'->Обновляем записи в таблицу - {schema}.{table_name}  <-')

        load_settings_url = (
            f'{config["psql_conn_type"]}ql+psycopg2://'
            f'{config["psql_login"]}:{config["psql_password"]}'
            f'@{config["psql_hostname"]}:{config["psql_port"]}'
            f'/{config["psql_name_bd"]}'
        )

        update_query = sql_processor.get_query_from_sql_file(
            name_sql_file,
            base_dir,
            query_dir=name_sql_dir,
            params_names=params_names,
            params_values=params_values,
            expanding=expanding,
        )

        engine = sa.create_engine(load_settings_url)
        with engine.connect() as connection:
            connection.execute(text(update_query))
            logger.info(f'->Записи в таблице - {schema}.{table_name} обновлены <-')
            connection.detach()

    except Exception as e:
        logger.error(f'->Ошибка {e} при загрузке данных в таблицу - {schema}.{table_name} <-')
        raise e
