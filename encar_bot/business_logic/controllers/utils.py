import logging
from typing import Any

import requests
from urllib.parse import urlparse
from django.db.models import Q

from business_logic.telegram_tasks import tg_message_task
from business_logic.models import Person

logger = logging.getLogger('db_logger')


def exist_user_check_status(telegram_id: str, telegram_username: str) -> Any | None:
    user = Person.objects.filter(Q(telegram_id=str(telegram_id)) |
                                 Q(telegram_username=str(telegram_username)))

    if user.exists():
        return Person.objects.filter(Q(telegram_id=str(telegram_id)) |
                                     Q(telegram_username=str(telegram_username)))
    else:
        return None


def is_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) or bool(parsed_url.netloc) or bool(parsed_url.path)


def make_api_request(url: str, params: dict, headers: dict, telegram_id: str,
                     task_type: str) -> bool | requests.Response:

    try:
        response = requests.get(url, params=params, headers=headers)
    except Exception as e:
        logger.error(f'Задача - {task_type} для telegram - {telegram_id}, ошибка при запросе api - {e}')
        return False

    if response.status_code != 200:
        handle_error_response(telegram_id, task_type, url, response, params)
        return True

    return response


def handle_error_response(telegram_id: str, task_type: str, api_type: str, response: requests.Response,
                          params: dict) -> bool:
    if response.status_code == 400 and response.json().get("error"):
        error_message = response.json()["error"]
        if "does not exist" in error_message:
            logger.error(f'Задача - {task_type} по {api_type} для telegram - {telegram_id}, ошибка при запросе api, '
                         f'нет таких параметров - {str(params)}')
            tg_message_task.apply_async(kwargs={'telegram_id': telegram_id,
                                                'message': "Информации о данном значении нет в системе"},
                                        countdown=0)
            logger.info(f'Задача tg_reminder(нет в системе) для клиента {telegram_id} из задачи {task_type} создана')
            return True

    logger.error(f'Задача - {task_type} по {api_type}  для telegram - {telegram_id} с параметрами - {str(params)}, '
                 f'ошибка при запросе api, некорректный  HTTP-статус код {response.status_code} '
                 f'запрос - {response.text}')
    tg_message_task.apply_async(kwargs={'telegram_id': telegram_id,
                                        'message': "Ошибка запроса, обратитесь к администратору"},
                                countdown=0)
    logger.info(f'Задача tg_reminder(ошибка) для клиента {telegram_id} из задачи {task_type}  создана')
    return True
