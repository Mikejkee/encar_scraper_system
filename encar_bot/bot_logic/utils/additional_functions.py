import sys
import logging
from os.path import dirname, realpath

from asgiref.sync import sync_to_async

begin_path = dirname(dirname(dirname(realpath(__file__))))
sys.path.append(begin_path)

from business_logic.telegram_tasks import (save_client_task, api_request_car_info_task, api_request_filters_task,
                                           api_delete_filter_task, api_create_filter_task)

logger = logging.getLogger('db_logger')


@sync_to_async
def save_client(name: str = None, surname: str = None, patronymic: str = None, person_fio: str = None,
                date_of_birth: str = None, phone_number: str = None, telegram_chat_id: str = None,
                telegram_id: str = None, telegram_username: str = None, telegram_name: str = None,
                telegram_surname: str = None, email: str = None, background_image: str = None):
    client_task = save_client_task.delay(name, surname, patronymic, person_fio, date_of_birth, phone_number,
                                         telegram_chat_id, telegram_id, telegram_username, telegram_name,
                                         telegram_surname, email, background_image)

    logger.info(f'Задача создана - save_client_task, id - {client_task.task_id}')


@sync_to_async
def check_user_status(telegram_id: str):
    # Заглушка для реализации платной подписки, основанной на ролях
    return True


@sync_to_async
def request_car(message_car: str, telegram_id: str):
    request_car_task = api_request_car_info_task.delay(message_car, telegram_id)
    logger.info(f'Задача создана - request_api_car_info_task, id - {request_car_task.task_id}')
    return True


@sync_to_async
def request_car_insurance(message: str, telegram_id: str):
    logger.info(f'Задача создана - request_api_car_insurance_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_car_diagnostic(message: str, telegram_id: str):
    logger.info(f'Задача создана - request_api_car_diagnostic_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_car_analytic(message: str, telegram_id: str):
    logger.info(f'Задача создана - request_api_car_analytic_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_analytic_cost(message: str, telegram_id: str):
    logger.info(f'Задача создана - request_analytic_cost_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_analytic_damage(message: str, telegram_id: str):
    logger.info(f'Задача создана - request_analytic_damage_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_filter(telegram_id: str):
    request_filter_task = api_request_filters_task.delay(telegram_id, telegram_id)
    logger.info(f'Задача создана - request_filter_task, id - {request_filter_task.task_id}')
    return True


@sync_to_async
def create_filter(telegram_id: str, title: str, link: str, brand: str, model: str, generation: str):
    create_filter_task = api_create_filter_task.delay(telegram_id, title, link, brand, model, generation)
    logger.info(f'Задача создана - create_filter_task, id - {create_filter_task.task_id}')
    return True


@sync_to_async
def delete_filter(telegram_id: str, filter_id: str):
    delete_filter_task = api_delete_filter_task.delay(telegram_id, filter_id)
    logger.info(f'Задача создана - delete_api_filter_task, id - {delete_filter_task.task_id}')
    return True
