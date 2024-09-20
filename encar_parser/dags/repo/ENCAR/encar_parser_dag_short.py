from os.path import dirname, realpath
import sys

from airflow.decorators import dag, task
from airflow.utils.trigger_rule import TriggerRule

begin_path = dirname(dirname(dirname(dirname(realpath(__file__)))))
sys.path.append(begin_path)

from dags.repo.ENCAR.regular_encar_parser import *


default_args = {
    "owner": "Encar",
    "depends_on_past": False,
    "start_date": datetime(2023, 9, 11),
    # "email": ["yumimo@yandex.ru"],
    # "email_on_failure": False,
    # "email_on_retry": False,
    # "retries": 5,
    # "retry_delay": timedelta(minutes=1),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
}


@dag(
    "encar_parser_short",
    default_args=default_args,
    # schedule_interval='0 0 * * *',
    schedule_interval='*/10 * * * *',
    # schedule_interval='* * * */1 *',  # для тестов
    catchup=False,
)
def encar_parsing_taskflow():
    @task()
    def take_searches_task():
        result = take_searches_function()
        return result

    @task()
    def period_check_searches_task(input_search_list):
        result = period_check_searches_function(input_search_list)
        return result

    @task()
    def encar_parser_task(parser_list):
        encar_parser_function(parser_list, full_parser_flag=False)

    search_list = take_searches_task()
    checked_search_list = period_check_searches_task(search_list)
    encar_parser_task(checked_search_list)


encar_parsing_taskflow()
