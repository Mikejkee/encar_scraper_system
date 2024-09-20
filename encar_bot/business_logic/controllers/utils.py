import logging
from urllib.parse import urlparse

import requests
from django.db.models import Q

from business_logic.telegram_tasks import *
from business_logic.models import *

logger = logging.getLogger('db_logger')


def tg_reminder(telegram_id, message, time=0):
    task = tg_message_task.apply_async(kwargs={'telegram_id': telegram_id, 'message': message}, countdown=time)
    return task.task_id


def exist_user_check_status(telegram_id, telegram_username):
    user = Person.objects.filter(Q(telegram_id=str(telegram_id)) |
                                 Q(telegram_username=str(telegram_username)))

    if user.exists():
        return Person.objects.filter(Q(telegram_id=str(telegram_id)) |
                                     Q(telegram_username=str(telegram_username)))


def is_url(url):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) or bool(parsed_url.netloc) or bool(parsed_url.path)


def process_car_info(telegram_id, request_return, api_type):
    tg_reminder(telegram_id, f"Информация о машине - {request_return['car_data']}")

    if request_return['inspection_data']:
        tg_reminder(telegram_id, f"Информация о диагностике - {request_return['inspection_data']}")

    if request_return['insurance_data']:
        tg_reminder(telegram_id, f"Информация о страховке - {request_return['insurance_data']}")

    logger.info(f'Задачи tg_reminder(успех) для клиента {telegram_id} из request_api_car_info по {api_type} созданы')


def make_api_request(url, params, headers, telegram_id, task_type):
    try:
        response = requests.get(url, params=params, headers=headers)
    except Exception as e:
        logger.warning(f'Задача - {task_type} для telegram - {telegram_id}, ошибка при запросе api - {e}')
        return None
    return response


def handle_error_response(telegram_id, task_type, api_type, response, message):
    if response.status_code == 400 and response.json().get("error"):
        error_message = response.json()["error"]
        if "does not exist" in error_message:
            logger.warning(f'Задача - {task_type} по {api_type} для telegram - {telegram_id}, ошибка при запросе api, '
                           f'нет такой машины - {message}')
            tg_reminder(telegram_id, "Информации о данной машине нет в системе")
            logger.info(f'Задача tg_reminder(нет машины) для клиента {telegram_id} из request_api_car_info создана')
            return True

    logger.warning(f'Задача - {task_type} по {api_type}  для telegram - {telegram_id}, ошибка при запросе api, '
                   f'некорректный  HTTP-статус код {response.status_code} запрос - {response.text}')
    tg_reminder(telegram_id, "Ошибка запроса, обратитесь к администратору")
    logger.info(f'Задача tg_reminder(ошибка) для клиента {telegram_id} из request_api_car_info создана')
    return True
