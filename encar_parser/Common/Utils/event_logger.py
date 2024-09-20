import io
import locale
import os
import textwrap
from dataclasses import dataclass


@dataclass
class SQLExtractor:

    @staticmethod
    def guess_encoding(file):
        """COMMON Метод определяет кодировку файла SQL-запроса"""
        print(file)
        with io.open(file, "rb") as f:
            data = f.read(5)
        if data.startswith(b"\xEF\xBB\xBF"):
            return "utf-8-sig"
        elif data.startswith(b"\xFF\xFE") or data.startswith(b"\xFE\xFF"):
            return "utf-16"
        else:
            try:
                with io.open(file, encoding="utf-8"):
                    return "utf-8"
            except:
                return locale.getdefaultlocale()[1]

    @staticmethod
    def get_query_from_sql_file(file_name, base_dir, params=None):
        """COMMON Метод возвращает SQL-запрос в строковом виде из SQL-файла"""
        need_path = os.path.join(base_dir, 'sql_queries', file_name)
        with open(need_path, 'r', encoding=SQLExtractor.guess_encoding(need_path)) as sql_file:
            lines = sql_file.read()
            query_string = textwrap.dedent(f"""{lines}""").replace('?', '{}')
            if params:
                if isinstance(params, str):
                    query_string = query_string.format(params)
                elif isinstance(params, dict):
                    query_string = query_string.format(**params)
                else:
                    query_string = query_string.format(*params)

            return query_string


@dataclass
class RunLogger(SQLExtractor):
    """Базовый класс журналирования событий и статистики основной задачи Run"""

    run_id: int = 'NULL'
    task_type: str = 'NULL'
    datetime_start: str = 'NULL'
    datetime_stop: str = 'NULL'

    total_count_extract_records: int = 'NULL'
    total_count_extract_regions: int = 'NULL'
    total_count_extract_mails: int = 'NULL'
    total_count_extract_files: int = 'NULL'

    total_count_new_records: int = 'NULL'
    total_count_new_regions: int = 'NULL'
    total_count_new_mails: int = 'NULL'
    total_count_new_files: int = 'NULL'

    total_count_load_records: int = 'NULL'
    total_count_load_regions: int = 'NULL'
    total_count_load_mails: int = 'NULL'
    total_count_load_files: int = 'NULL'

    total_time: int = 'NULL'

    array_of_steps: list = 'NULL'

    def insert_run(self, connection, task_type, run_start):
        self.task_type = f"'{task_type}'"
        self.datetime_start = run_start.strftime("'%Y-%m-%d %H:%M:%S'")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        query_str = self.get_query_from_sql_file('insert_new_run_query.sql', base_dir)
        query_string = textwrap.dedent(f"""{query_str}""").replace('?', '{}')
        params = (self.task_type, self.datetime_start)
        query_string = query_string.format(*params)
        new_run = connection.execute(query_string)
        return new_run.fetchone()[0]

    def update_run(self, connection):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        query_str = self.get_query_from_sql_file('update_new_run_query.sql', base_dir)
        query_string = textwrap.dedent(f"""{query_str}""").replace('?', '{}')
        if self.datetime_stop != 'NULL':
            self.datetime_stop = self.datetime_stop
        params = (self.datetime_stop, self.total_count_extract_records, self.total_count_extract_regions,
                  self.total_count_extract_mails, self.total_count_extract_files, self.total_count_new_records,
                  self.total_count_new_regions, self.total_count_new_mails, self.total_count_new_files,
                  self.total_count_load_records, self.total_count_load_regions, self.total_count_load_mails,
                  self.total_count_load_files, self.total_time, self.run_id)
        print(params)
        query_string = query_string.format(*params)
        update_run = connection.execute(query_string)
        return update_run

    def process_updating_steps(self, connection):
        for step in self.array_of_steps:
            step.update_step(connection)


@dataclass
class StepLogger(SQLExtractor):
    """Класс журналирования событий и статистики шага Step - элемента задачи Run"""

    run_id: int = 'NULL'
    step_id: int = 'NULL'
    step_type: str = 'NULL'
    datetime_start: str = 'NULL'
    datetime_stop: str = 'NULL'

    total_count_extract_records: int = 'NULL'
    total_count_extract_regions: int = 'NULL'
    total_count_extract_mails: int = 'NULL'
    total_count_extract_files: int = 'NULL'

    total_count_new_records: int = 'NULL'
    total_count_new_regions: int = 'NULL'
    total_count_new_mails: int = 'NULL'
    total_count_new_files: int = 'NULL'

    total_count_load_records: int = 'NULL'
    total_count_load_regions: int = 'NULL'
    total_count_load_mails: int = 'NULL'
    total_count_load_files: int = 'NULL'

    total_time: int = 'NULL'

    array_of_items: list = 'NULL'

    def insert_step(self, connection, step_type, step_start, run_id):
        self.step_type = f"'{step_type}'"
        self.datetime_start = step_start.strftime("'%Y-%m-%d %H:%M:%S'")
        self.run_id = run_id
        base_dir = os.path.dirname(os.path.abspath(__file__))
        query_str = self.get_query_from_sql_file('insert_new_step_query.sql', base_dir)
        query_string = textwrap.dedent(f"""{query_str}""").replace('?', '{}')
        params = (self.run_id, self.step_type, self.datetime_start)
        query_string = query_string.format(*params)
        new_run = connection.execute(query_string)
        return new_run.fetchone()[0]

    def update_step(self, connection):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        query_str = self.get_query_from_sql_file('update_new_step_query.sql', base_dir)
        query_string = textwrap.dedent(f"""{query_str}""").replace('?', '{}')
        if self.datetime_stop != 'NULL':
            self.datetime_stop = self.datetime_stop

        params = (self.datetime_stop, self.total_count_extract_records, self.total_count_extract_regions,
                  self.total_count_extract_mails, self.total_count_extract_files, self.total_count_new_records,
                  self.total_count_new_regions, self.total_count_new_mails, self.total_count_new_files,
                  self.total_count_load_records, self.total_count_load_regions, self.total_count_load_mails,
                  self.total_count_load_files, self.total_time, self.step_id)
        print(params)
        query_string = query_string.format(*params)
        update_run = connection.execute(query_string)
        return update_run

    def process_updating_items(self, connection):
        for item in self.array_of_items:
            item.update_item(connection)


@dataclass
class ItemLogger(SQLExtractor):
    """Класс журналирования событий и статистики элемента Item - элемента шага Step"""

    step_id: int = 'NULL'
    item_id: int = 'NULL'
    item_type: str = 'NULL'
    sub_item_type: str = 'NULL'
    datetime_start: str = 'NULL'
    datetime_stop: str = 'NULL'

    total_count_extract_records: int = 'NULL'
    total_count_extract_regions: int = 'NULL'
    total_count_extract_mails: int = 'NULL'
    total_count_extract_files: int = 'NULL'

    total_count_new_records: int = 'NULL'
    total_count_new_regions: int = 'NULL'
    total_count_new_mails: int = 'NULL'
    total_count_new_files: int = 'NULL'

    total_count_load_records: int = 'NULL'
    total_count_load_regions: int = 'NULL'
    total_count_load_mails: int = 'NULL'
    total_count_load_files: int = 'NULL'

    total_time: int = 'NULL'

    def insert_item(self, connection, item_type, sub_item_type, item_start, step_id):
        self.item_type = f"'{item_type}'"
        self.sub_item_type = f"'{sub_item_type}'"
        self.datetime_start = item_start.strftime("'%Y-%m-%d %H:%M:%S'")
        self.step_id = step_id
        base_dir = os.path.dirname(os.path.abspath(__file__))
        query_str = self.get_query_from_sql_file('insert_new_item_query.sql', base_dir)
        query_string = textwrap.dedent(f"""{query_str}""").replace('?', '{}')
        params = (self.step_id, self.item_type, self.sub_item_type, self.datetime_start)
        query_string = query_string.format(*params)
        new_run = connection.execute(query_string)
        return new_run.fetchone()[0]

    def update_item(self, connection):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        query_str = self.get_query_from_sql_file('update_new_item_query.sql', base_dir)
        query_string = textwrap.dedent(f"""{query_str}""").replace('?', '{}')
        if self.datetime_stop != 'NULL':
            self.datetime_stop = self.datetime_stop
        params = (self.datetime_stop, self.total_count_extract_records, self.total_count_extract_regions,
                  self.total_count_extract_mails, self.total_count_extract_files, self.total_count_new_records,
                  self.total_count_new_regions, self.total_count_new_mails, self.total_count_new_files,
                  self.total_count_load_records, self.total_count_load_regions, self.total_count_load_mails,
                  self.total_count_load_files, self.total_time, self.item_id)
        print(params)
        query_string = query_string.format(*params)
        update_run = connection.execute(query_string)
        return update_run
