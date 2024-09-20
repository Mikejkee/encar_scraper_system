import configparser
import email
import imaplib
import io
import locale
import os
import textwrap
import pandas as pd
import sqlalchemy as sa

from dataclasses import dataclass
from datetime import datetime, timedelta
from email.header import decode_header
from ftplib import FTP_TLS, FTP
from pandas import DataFrame
from pathlib import Path
from typing import Any, List, Union

from .config_logger import BaseLogger


@dataclass
class SQLProcessor(BaseLogger):
    """Базовый класс для соединения с БД и SQL-запросов
        COMMON - методы для любого логического блока;
        EXTRACT - методы выгрузки данных из БД;
        LOAD - методы загрузки данных в БД;
        REGIONS - методы работы с данными по регионам;
        FTPS - методы выгрузки и загрузки файлов в БД;
        MAIL - методы парсинга электронной почты.
    """

    extract_settings_url: str = None
    region_settings_url: str = None
    load_settings_url: str = None
    settings_url: str = None

    extract_settings_engine: object = None
    region_settings_engine: object = None
    load_settings_engine: object = None
    settings_engine: sa.engine.Engine = None

    extract_settings_connection: object = None
    region_settings_connection: object = None
    load_settings_connection: object = None
    settings_connection: sa.engine.Connection = None

    inside_logger: object = None

    @staticmethod
    def config(file_dir: str, file_name: str) -> dict:
        """COMMON Метод осуществляет парсинг конфигурационного файла и возвращает словарь
           :param str file_dir: название директории файлов
           :param str file_name: название файла
        """
        common_dir = Path(os.path.dirname(os.path.realpath(__file__))).parent.parent
        need_path = os.path.join(common_dir, file_dir, file_name)
        result = dict()
        config = configparser.ConfigParser()
        config.read(need_path)
        auth, data, mode = config['AUTH'], config['DATA'], config['MODE']
        for key, value in auth.items():
            result.update({key: value})
        for key, value in data.items():
            result.update({key: value})
        for key, value in mode.items():
            result.update({key: value})
        return result

    # COMMON LOGIC
    @staticmethod
    def guess_encoding(file_path: str) -> str:
        """ COMMON Метод определяет кодировку файла SQL-запроса
            :param str file_path: Путь к файлу
        """
        with io.open(file_path, "rb") as f:
            data = f.read(5)
        if data.startswith(b"\xEF\xBB\xBF"):
            return "utf-8-sig"
        elif data.startswith(b"\xFF\xFE") or data.startswith(b"\xFE\xFF"):
            return "utf-16"
        else:
            try:
                with io.open(file_path, encoding="utf-8"):
                    return "utf-8"
            except:
                return locale.getdefaultlocale()[1]

    @staticmethod
    def get_query_from_sql_file(file_name: str, base_dir: str, params_names: object = None,
                                params_values: object = None, expanding: bool = True,
                                query_dir: str = 'sql_queries') -> str:
        """ COMMON Метод возвращает SQL-запрос в строковом виде из SQL-файла
            :param str file_name: Название файла SQL
            :param str base_dir: Путь к базовой директории проекта
            :param object params_names: Параметры табличных имен запроса - строка, словарь или кортеж
            :param object params_values: Параметры значений запроса - список, кортеж или словарь
            :param bool expanding: Параметр expanding для sa.bindparam
            :param str query_dir: Директория с запросами
        """
        need_path = os.path.join(base_dir, query_dir, file_name)
        with open(need_path, 'r', encoding=SQLProcessor.guess_encoding(need_path)) as sql_file:
            lines = sql_file.read()
            query_string = textwrap.dedent(f"""{lines}""").replace('?', '{}')
            if params_names:
                if isinstance(params_names, str):
                    query_string = query_string.format(params_names)
                elif isinstance(params_names, dict):
                    query_string = query_string.format(**params_names)
                else:
                    try:
                        query_string = query_string.format(*params_names)
                    except Exception as e:
                        print(e)
                        raise ValueError('Параметры табличных имен запроса не валидны!')

            if params_values:
                query_string = sa.text(query_string)
                names_list = params_values
                if isinstance(params_values, dict):
                    names_list = params_values.keys()
                for key in names_list:
                    query_string = query_string.bindparams(sa.bindparam(key, expanding=expanding))

            return query_string

    def sql_query(self, sql_query: str, connection: object, params: dict = None) -> object:
        """ COMMON Метод выполняет SQL запрос
            :param str sql_query: строка запроса SQL
            :param object connection: объект соединения
            :param dict params: параметры запроса
        """
        if params:
            return connection.execute(sql_query, params)
        return connection.execute(sa.text(sql_query))

    def get_max_value(self, name_value: str, table_name: str, connection: object, url: str = None,
                      db_name: str = None, default_value: Any = 0) -> Any:
        """ COMMON Метод вычисляет максимальное значение столбца таблицы
            :param str name_value: название вычисляемого максимального значения
            :param str table_name: название таблицы
            :param object connection: объект соединения
            :param str url: url источника
            :param str db_name: название БД
            :param Any default_value: значение по-умолчанию
        """
        if isinstance(default_value, str):
            default_value = "'" + default_value + "'"
        if url and db_name:
            max_value_df = pd.read_sql(f'SELECT COALESCE(MAX({name_value}), {default_value}) AS max_val FROM "{table_name}" '
                                       f"WHERE source_url = '{url}' AND source_db = '{db_name}';",
                                       connection)
        else:
            max_value_df = pd.read_sql(f'SELECT COALESCE(MAX({name_value}), {default_value}) AS max_val FROM "{table_name}";',
                                       connection)
        max_value = max_value_df['max_val'][0]
        return max_value

    def create_connection(self, dialect: str = None, driver: str = None, login: str = None, password: str = None,
                          host: str = None, port: int = None, db: str = None, url: str = None,
                          **kwargs) -> sa.engine.Connection:
        """ COMMON Метод создает engine для соединение с БД.
            :param str dialect: диалект SQL
            :param str driver: драйвер SQL
            :param str login: логин для соединения
            :param str password: пароль для соединения
            :param str host: host сервера
            :param int port: port сервера (необязательный,
            при отсутствии будет использоваться 3306 для MySQL и 5432 для PostgreSQL)
            :param str db: имя базы данных
            :param str url: готовый url (если есть). Используется, как предпочтительный
        """
        if url:
            self.settings_url = url
        else:
            if dialect is None or driver is None or login is None or password is None or host is None or db is None:
                raise ValueError("Since 'url' is not specified, arguments 'dialect', 'driver', 'login', 'password', "
                                 "'host' and 'db' are required!")
            if dialect == 'mysql' and not port:
                port = 3306
            if dialect == 'postgresql' and not port:
                port = 5432
            self.settings_url = f"{dialect}+{driver}://{login}:{password}@{host}:{port}/{db}"

        self.current_logger.info(f'Prepare variables: url: {self.settings_url}')
        self.settings_engine = sa.create_engine(self.settings_url, **kwargs)
        self.settings_connection = self.settings_engine.connect()
        return self.settings_connection


    # EXTRACT LOGIC
    def create_extract_engine(self, **kwargs) -> object:
        """EXTRACT Метод создает engine для соединения с БД"""
        self.extract_settings_engine = sa.create_engine(self.extract_settings_url, **kwargs)
        return self.extract_settings_engine

    def extract_settings_connect(self) -> object:
        """EXTRACT Метод создает соединение с БД"""
        self.extract_settings_connection = self.extract_settings_engine.connect()
        return self.extract_settings_connection

    def extract_data_sql(self, sql_query: str, params: dict = None, connection: object = None, chunksize: int = None, parse_dates: bool = True) -> DataFrame:
        """ EXTRACT Метод осуществляет чтение SQL-запроса или таблицы базы данных в DataFrame
            :param str sql_query: строка запроса SQL
            :param dict params: параметры для read_sql pandas
            :param object connection: объект соединения
            :param int chunksize: размер пакета
            :param bool parse_dates: парсинг дат
        """
        current_connection = self.extract_settings_connection
        if connection:
            current_connection = connection
        return pd.read_sql(sql_query, current_connection, params=params, chunksize=chunksize, parse_dates=parse_dates)

    def get_check_list(self, check_field: str, table_name: str) -> List:
        """ EXTRACT Метод выгружает список уже загруженных файлов в DataFrame
            :param str check_field: столбец для проверки
            :param str table_name: название таблицы
        """
        with self.extract_settings_connect() as connection:
            self.sql_query('SET SCHEMA \'public\'', connection)
            filename_df = self.extract_data_sql('SELECT ' + check_field + ' FROM "' + table_name + '"')
            check_list = filename_df[check_field].to_list()

            connection.detach()
        connection.close()

        return check_list

    # REGION LOGIC
    def get_regions(self, white_list: list = None, black_list: list = None) -> DataFrame:
        """ REGIONS Метод выгружает все регионы в DataFrame
            :param list white_list: белый список регионов
            :param list black_list: черный список регионов
        """
        sql_query_text = 'select * from "ProjectsASOP" where active=true '
        params = {}
        if white_list and isinstance(white_list, list):
            white_list = [str(el) for el in white_list]
            sql_query_text = sql_query_text + 'and region in :white_list'
            params.update({'white_list': white_list})
        if black_list and isinstance(black_list, list):
            black_list = [str(el) for el in black_list]
            sql_query_text = sql_query_text + ' and region not in :black_list'
            params.update({'black_list': black_list})

        sql_query_text = sql_query_text + ' order by id;'

        query = sa.text(sql_query_text)
        if white_list:
            query = query.bindparams(sa.bindparam('white_list', expanding=True))
        if black_list:
            query = query.bindparams(sa.bindparam('black_list', expanding=True))

        regions = pd.read_sql(query, con=self.region_settings_connection, params=params)
        print('REGIONS - ', regions)
        return regions

    def create_region_engine(self, **kwargs) -> object:
        """REGIONS Метод создает engine для соединения с БД"""
        self.region_settings_engine = sa.create_engine(self.region_settings_url, **kwargs)
        return self.region_settings_engine

    def region_settings_connect(self) -> object:
        """REGIONS Метод создает соединение с БД"""
        self.region_settings_connection = self.region_settings_engine.connect()
        return self.region_settings_connection

    # FTPS LOGIC
    def extract_from_ftps(self, login: str, password: str, url: str, local_path: str, cwd_directory: str,
                          file_substring: str, table_name: str, tls: int = 0,
                          black_list: list = None) -> tuple:
        """ FTPS Метод получает список всех файлов в директории сервера и недостающие скачивает в буферную директорию
            :param str login: логин авторизации соединения ftp(s)
            :param str password: пароль авторизации соедниения ftp(s)
            :param str url: адрес соединения ftp(s)
            :param str local_path: локальный путь сохранения файлов
            :param str cwd_directory: директория файлов
            :param str file_substring: подстрока файла
            :param str table_name: название таблицы выгрузки чек-листа
            :param int tls: открытое/закрытое соединение
            :param list black_list: черный список файлов
        """
        cor_files = []
        check_list = self.get_check_list('file_name', table_name)
        if tls == 1:
            ftps = FTP_TLS(url)
        else:
            ftps = FTP(url)
        if black_list is None:
            black_list = []
        ftps.login(login, password)
        ftps.prot_p()
        ftps.cwd(cwd_directory)
        for file in ftps.nlst():
            if (file_substring in file) and (os.path.splitext(file)[0] not in check_list) and (
                    os.path.splitext(file)[1] == '.csv') and (file not in black_list):
                # скачиваются все файлы, формируемые по transaction_date
                # из регионов нет Волгограда, тк по нему файлы формируются по status_date
                cor_files.append(file)
            else:
                continue
        for filename in cor_files:
            ftps.retrbinary("RETR " + filename, open(os.path.join(local_path, filename), 'wb').write)
        ftps.close()
        print("New files: ", cor_files)
        return check_list, cor_files

    def load_to_ftps(self, login: str, password: str, url: str, file_path: str, filename: str, cwd_directory: str,
                     tls: int = 0) -> None:
        """ FTPS Метод загружает список всех файлов в директорию на сервер
            :param str login: логин авторизации соединения ftp(s)
            :param str password: пароль авторизации соедниения ftp(s)
            :param str url: адрес соединения ftp(s)
            :param str file_path: путь к файлам
            :param str filename: название файла
            :param str cwd_directory: директория файлов
            :param int tls: открытое/закрытое соединение
        """
        if tls == 1:
            ftps = FTP_TLS(url)
        else:
            ftps = FTP(url)
        ftps.login(login, password)
        ftps.cwd(cwd_directory)
        ftps.storbinary("STOR " + filename, open(os.path.join(file_path, filename), 'rb'))
        os.remove(os.path.join(file_path, filename))

    def copy_expert_to_file(self, query: str, file: object, connection: object) -> None:
        """FTPS Метод копирует данные из таблицы БД в файл
            :param str query: строка запроса
            :param object file: файл
            :param object connection: объект соединения
        """
        cursor = connection.connection.cursor()
        cursor.copy_expert(query, file)

    # LOAD LOGIC
    def create_load_engine(self, **kwargs) -> object:
        """LOAD Метод создает engine для соединения с БД"""
        self.load_settings_engine = sa.create_engine(self.load_settings_url, **kwargs)
        return self.load_settings_engine

    def load_settings_connect(self) -> object:
        """LOAD Метод создает соединение с БД"""
        self.load_settings_connection = self.load_settings_engine.connect()
        return self.load_settings_connection

    def load_data_sql(self, dataframe: DataFrame, table: str, truncate: bool = False,
                      connection: sa.engine.Connection = None, **kwargs) -> object:
        """ LOAD Метод осуществляет загрузку записей, хранящихся в DataFrame, в БД
            :param DataFrame dataframe: датафрейм
            :param str table: название таблицы
            :param bool truncate: режим загрузки
            :param sa.engine.Connection connection: использует предложенное соединение,
            вместо self.load_settings_connection по умолчанию
        """
        if_exists = 'append'
        if truncate:
            if_exists = 'replace'
        if not connection:
            connection = self.load_settings_connection
        return dataframe.to_sql(table, connection, if_exists=if_exists, index=False, **kwargs)

    # MAIL LOGIC
    def process_mail(self, host: str, login: str, password: str, check_list: list, cycle_process=None,
                     load_process=None, **kwargs) -> Union[bool, DataFrame, list]:
        """MAIL Метод формирует список писем для обработки в цикле
            :param str host: хост подключения ЭП
            :param str login: логин авторизации ЭП
            :param str password: пароль авторизации ЭП
            :param list check_list: список существующих в базе mail_id
            :param function cycle_process: функция парсинга почты
            :param function load_process: функция загрузки в базу
        """
        imaplib._MAXLINE = 100000
        imap_ssl = None
        try:
            imap_ssl = imaplib.IMAP4_SSL(host, port=993)
            print("Logging into mailbox...")
            resp_code_login, response_login = imap_ssl.login(login, password)
        except Exception as e:
            print(f"ErrorType : {type(e).__name__}, Error : {e}")
            resp_code_login, response_login = None, None
        print(f"Response Code Login: {resp_code_login}")
        print(f"Response Login: {response_login[0].decode()}\n")

        if imap_ssl:
            try:
                resp_code_list, directories = imap_ssl.list()
            except Exception as e:
                print(f"ErrorType : {type(e).__name__}, Error : {e}")
                resp_code_list, directories = None, None
            print(f"Response Code List: {resp_code_list}")

            print("========= List of Directories =================\n")
            for directory in directories:
                print(directory.decode())

            print("\n=========== Mail Count in INBOX ===============\n")
            try:
                resp_code_inbox, mail_count = imap_ssl.select('INBOX', readonly=True)
            except Exception as e:
                print(f"INBOX - ErrorType : {type(e).__name__}, Error : {e}")
                resp_code_inbox, mail_count = None, None
            print(int(mail_count[0].decode('utf-8')))

            date_from_start = kwargs.get('datetime_from')
            if not date_from_start:
                date_from_start = '01-Nov-2022'

            date_from_to = kwargs.get('datetime_to')
            if not date_from_to:
                date_from_to = (datetime.now() + timedelta(days=1)).strftime('%d-%b-%Y')

            print(f'(SINCE "{date_from_start}" BEFORE "{date_from_to}")')
            resp_code_search, mails = imap_ssl.search(None, f'(SINCE "{date_from_start}" BEFORE "{date_from_to}")')
            print(f'Searched')

            recieved_mail_ids = set(mails[0].decode().split())
            print(f'Recieved {len(recieved_mail_ids)}')

            if check_list:
                print('check')
                filtered_mail_ids = recieved_mail_ids - set(check_list)
            else:
                filtered_mail_ids = recieved_mail_ids
            print(f"PERIOD COUNT: {len(filtered_mail_ids)}")
            print(f"Mail IDs : {filtered_mail_ids}\n")

            processed_data = []
            sender = kwargs.get('sender')
            for mail_id in filtered_mail_ids:
                print(f"================== OUTER Cycle of Mail [{mail_id}] ====================")
                resp_code, mail_data = imap_ssl.fetch(mail_id, '(RFC822)')
                message = email.message_from_bytes(mail_data[0][1])

                pre_date_processed = message['Date'].split('+')[0]
                if '-0000' in pre_date_processed:
                    date_processed = pre_date_processed.replace('-0000', '')
                else:
                    date_processed = pre_date_processed
                datetime_email = datetime.strptime(date_processed.strip(), "%a, %d %b %Y %H:%M:%S")
                from_msg = str(message.get('From')).split(' ')[-1]

                subject_tuple = decode_header(message['Subject'])[0]
                try:
                    subject = subject_tuple[0].decode(subject_tuple[1])
                except Exception as e:
                    print('Decode error: ', e)
                    subject = subject_tuple[0]
                if sender:
                    if sender == from_msg:
                        processed_data.append({'mail_id': mail_id, 'subject': subject, 'message': message,
                                               'datetime_email': datetime_email, 'from_msg': from_msg})
                    else:
                        continue
                else:
                    processed_data.append({'mail_id': mail_id, 'subject': subject, 'message': message,
                                           'datetime_email': datetime_email, 'from_msg': from_msg})
            imap_ssl.close()
            len_data = len(processed_data)
            print(f'LEN OF PROCESSED DATA {len_data}')

            if not cycle_process and not load_process:
                return processed_data

            if cycle_process:
                self.create_load_engine()
                if len_data > 0:
                    for pr in processed_data:
                        cycle_result = cycle_process([pr, ], **kwargs)
                        if ((isinstance(cycle_result, DataFrame) and cycle_result.shape[0] > 0) or (
                                isinstance(cycle_result, tuple) and len(cycle_result) > 0)) and load_process:
                            with self.load_settings_connect():
                                print(f'LOADING DF')
                                load_process(self, cycle_result, **kwargs)
                                print(f'DF LOADED')
                        else:
                            print('RESULT IS EMPTY')
            return False
        else:
            return False
