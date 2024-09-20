from pathlib import Path
import os

import pandas as pd
import sqlalchemy as sa

from Common.Utils.sql_processor import SQLProcessor


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


def get_data_of_db_psql(config: dict,
                        name_sql_file: str,
                        base_dir,
                        sql_params_name: str = "",
                        name_sql_dir: str = 'sql_query_files',
                        another_db: str = None) -> pd.DataFrame:
    bd_name = config["psql_name_bd"]
    if another_db:
        bd_name = another_db

    extract_settings_url = (f'postgresql+psycopg2://'
                            f'{config["psql_login"]}:{config["psql_password"]}'
                            f'@{config["psql_hostname"]}'
                            f'/{bd_name}')

    extract_query = SQLProcessor.get_query_from_sql_file(
        name_sql_file,
        base_dir,
        query_dir=name_sql_dir,
        params_names=sql_params_name,
    )

    engine = sa.create_engine(extract_settings_url)
    with engine.connect() as connection:
        data = pd.read_sql(extract_query, connection)
        connection.detach()

    return data


def get_data_of_db_mysql(config: dict,
                         name_sql_file: str,
                         base_dir,
                         name_sql_dir: str = 'sql_queries',
                         another_db: str = None) -> pd.DataFrame:
    bd_name = config["psql_name_bd"]
    if another_db:
        bd_name = another_db

    extract_settings_url = (f'mysql://'
                            f'{config["mysql_login"]}:{config["mysql_password"]}'
                            f'@{config["mysql_hostname"]}'
                            f'/{bd_name}')

    extract_query = SQLProcessor.get_query_from_sql_file(
        name_sql_file,
        base_dir,
        query_dir=name_sql_dir,
    )

    engine = sa.create_engine(extract_settings_url)
    with engine.connect() as connection:
        data = pd.read_sql(extract_query, connection)
        connection.detach()

    return data


def load_data_in_db(df: pd.DataFrame,
                    config: dict,
                    name_table_in_db: str,
                    schema: str,
                    exists='append',
                    another_db: str = None
                    ):
    bd_name = config["psql_name_bd"]
    if another_db:
        bd_name = another_db

    load_settings_url = (f'postgresql+psycopg2://'
                         f'{config["psql_login"]}:{config["psql_password"]}'
                         f'@{config["psql_hostname"]}'
                         f'/{bd_name}')

    engine = sa.create_engine(load_settings_url)
    with engine.connect() as connection:
        df.to_sql(
            name_table_in_db,
            con=connection,
            if_exists=exists,
            index=False,
            schema=schema,
        )
        connection.commit()
        connection.detach()


def get_of_str_dict_in_df(
        df_test: pd.DataFrame,
        name_column_str: str,
        list_column: list) -> pd.DataFrame:
    """
    Преобразует питоновскую строку вида - словарь, в питоновский словарь
    и разносит все "ключи" словаря по столбцам
    df_test - Dataframe для преобразования
    name_column - имя колонки, где лежит словарь
    list_column - список ключей, которые надо разнести по столбцам
    """
    import ast

    df_test[name_column_str] = df_test[name_column_str].apply(lambda x: ast.literal_eval(x))

    for name_column in list_column:
        df_test[name_column] = df_test[name_column_str].apply(lambda x: x[name_column])

    return df_test
