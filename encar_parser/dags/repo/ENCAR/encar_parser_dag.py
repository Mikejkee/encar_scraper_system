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
    "encar_parser",
    default_args=default_args,
    # schedule_interval='0 0 * * *',
    schedule_interval='0 10 * * *',
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
        encar_parser_function(parser_list, full_parser_flag=True)

    @task()
    def create_unique_card_task():
        create_unique_card_list()

    @task()
    def create_unique_insurance_task():
        create_unique_insurance_list()

    @task()
    def create_unique_inspection_task():
        create_unique_inspection_list()

    @task()
    def create_translate_tables():
        translate_tables()

    search_list = take_searches_task()
    checked_search_list = period_check_searches_task(search_list)
    (encar_parser_task(checked_search_list) >> create_unique_card_task() >> create_unique_insurance_task() >>
     create_unique_inspection_task() >> create_translate_tables())

    create_unique_card_task.trigger_rule = TriggerRule.ALL_DONE
    create_unique_insurance_task.trigger_rule = TriggerRule.ALL_DONE
    create_unique_inspection_task.trigger_rule = TriggerRule.ALL_DONE
    create_translate_tables.trigger_rule = TriggerRule.ALL_DONE


encar_parsing_taskflow()
