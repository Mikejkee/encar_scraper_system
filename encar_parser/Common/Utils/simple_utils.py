from pathlib import Path
import os
import re
import json
import logging

import pandas as pd
import sqlalchemy as sa

from Common.Utils.sql_processor import SQLProcessor
from sqlalchemy.exc import ResourceClosedError
import undetected_chromedriver as uc

sql_processor = SQLProcessor()


def check_and_create_dir_or_file_for_path_to_load(
        name_dir: str,
        file_name: str = None) -> Path:
    """
    Функция проверяет наличие директории, при отсутствии создает ее, и возвращает
    путь к указанной директории,а также файл внутри

    :param name_dir: имя директории
    :return:
    """

    dir_path = Path.cwd()

    if not os.path.exists(name_dir):
        os.mkdir(Path(dir_path, name_dir))

    if file_name:
        path_to_load = Path(dir_path, name_dir, file_name)
    else:
        path_to_load = Path(dir_path, name_dir)

    return path_to_load


def load_data_from_bd(logger,
                      config: dict,
                      name_sql_file: str,
                      base_dir,
                      schema,
                      table_name,
                      params_names: object = None,
                      params_values: object = None,
                      name_sql_dir: str = 'sql_query_files',
                      expanding: bool = True) -> pd.DataFrame:
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
                connection.detach()
                logger.info(f'->Выгрузка из таблицы - {schema}.{table_name} - успешна <-')
                return True

    except Exception as e:
        logger.error(f'->Ошибка {e} при выгрузке данных из таблицы - {schema}.{table_name} <-')
        raise e


def load_data_in_db(df: pd.DataFrame,
                    logger,
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


def update_data_in_db(logger, df: pd.DataFrame, config: dict, update_sql_file: str, drop_sql_file: str,
                      columns_info: dict, base_dir, schema: str, name_table_in_db: str,
                      name_sql_dir: str = 'sql_query_files'):
    try:
        logger.info(f'->Обновляем (вставляем новые данные) записи в таблице - {schema}.{name_table_in_db}  <-')

        sql_processor.load_settings_url = (
            f'{config["psql_conn_type"]}ql+psycopg2://'
            f'{config["psql_login"]}:{config["psql_password"]}'
            f'@{config["psql_hostname"]}:{config["psql_port"]}'
            f'/{config["psql_name_bd"]}'
        )

        update_query = sql_processor.get_query_from_sql_file(
            update_sql_file,
            base_dir,
            query_dir=name_sql_dir,
        )

        drop_query = sql_processor.get_query_from_sql_file(
            drop_sql_file,
            base_dir,
            query_dir=name_sql_dir
        )

        sql_processor.create_load_engine()

        metadata = sa.MetaData()
        columns = [sa.Column(name_column, type_column) for name_column, type_column in columns_info.items()]
        temp_table = sa.Table('temp_table', metadata, *columns)

        with sql_processor.load_settings_connect() as connection:
            metadata.create_all(connection)
            sql_processor.load_data_sql(
                dataframe=df,
                table='temp_table',
                connection=connection
            )

            sql_processor.sql_query(
                    update_query,
                    connection=connection,
            )

            sql_processor.sql_query(
                drop_query,
                connection=connection
            )

    except Exception as e:
        with sql_processor.load_settings_connect() as connection:
            sql_processor.sql_query(
                drop_query,
                connection=connection
            )
        logger.error(f'->Ошибка {e} при обновлении данных в таблице - {schema}.{name_table_in_db} <-')
        raise e


def cleaned_text(text):
    if text:
        return re.sub(r'[\n\t\s]', '', text)
    else:
        None


def convert_columns_to_json(data, columns):
    for col in columns:
        if isinstance(data[col], (list, dict)):
            data[col] = json.dumps(data[col])
        else:
            data[col] = data[col].apply(json.dumps)
    return data


def create_undetected_chrome_driver():
    options = uc.ChromeOptions()

    # Настройки для запуска из докера
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    # Опция для блокировки окон (тестировал)
    # options.add_argument("--disable-popup-blocking")

    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.set_page_load_timeout(35)
    return driver


def get_car_id_from_photo(car_id, photo_list):
    car_id_from_photo = car_id
    if photo_list:
        try:
            car_id_from_photo = re.search(r'.*?/(\d*?)_', photo_list[0]['url'])[1]
        except TypeError:
            car_id_from_photo = re.search(r'.*?/(\d*?)_', photo_list[0])[1]
    return car_id_from_photo


def fill_nulls(row):
    # Функция для заполнения нулевых значений
    filled_row = row.bfill()
    return filled_row.combine_first(row)


def get_df_with_last_existing_data_each_cell(dirty_data_df, full_data_df, group_column):
    merged_dirty_data_df = dirty_data_df.set_index(group_column).combine_first(full_data_df.set_index(group_column))
    grouped_merged_data_df = merged_dirty_data_df.groupby(group_column)
    cleaned_data_df = grouped_merged_data_df.apply(lambda group: fill_nulls(group).iloc[0])
    cleaned_data_df = cleaned_data_df.reset_index()

    return cleaned_data_df
