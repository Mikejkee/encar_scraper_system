import os

import asyncio
from celery import shared_task
from aiogram import Bot, Dispatcher

from mainmodule.celery import BaseTask

token = os.environ.get("TELEGRAM_TOKEN")
bot = Bot(token=token, parse_mode="HTML")
dp = Dispatcher()


@shared_task(base=BaseTask)
def tg_message_task(telegram_id: str, message: str):

    from .controllers.bot_services import tg_message

    loop = asyncio.get_event_loop()
    loop.run_until_complete(tg_message(bot, telegram_id, message=message))

    return True


@shared_task(base=BaseTask)
def save_client_task(name: str, surname: str, patronymic: str, person_fio: str, date_of_birth: str, phone_number: str,
                     telegram_chat_id: str, telegram_id: str, telegram_username: str, telegram_name: str,
                     telegram_surname: str, email: str, background_image: str):

    from .controllers.bot_services import save_user

    save_user('Клиент', name, surname, patronymic, person_fio, date_of_birth, phone_number,
              telegram_chat_id, telegram_id, telegram_username, telegram_name, telegram_surname,
              email, background_image)

    return True


@shared_task(base=BaseTask)
def api_request_car_info_task(message_car: str, telegram_id: str):

    from .controllers.bot_services import api_request_car_info

    api_request_car_info(message_car, telegram_id)

    return True


@shared_task(base=BaseTask)
def api_request_filters_task(telegram_id: str):

    from .controllers.bot_services import api_request_filters

    api_request_filters(telegram_id)

    return True


@shared_task(base=BaseTask)
def api_delete_filter_task(telegram_id: str, filter_id: str):

    from .controllers.bot_services import api_delete_filter

    api_delete_filter(telegram_id, filter_id)

    return True


@shared_task(base=BaseTask)
def api_create_filter_task(telegram_id: str, title: str, link: str, brand: str, model: str, generation: str):

    from .controllers.bot_services import api_create_filter

    api_create_filter(telegram_id, title, link, brand, model, generation)

    return True
