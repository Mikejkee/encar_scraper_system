import os

import asyncio
from celery import shared_task
from aiogram import Bot, Dispatcher

from mainmodule.celery import BaseTask

token = os.environ.get("TELEGRAM_TOKEN")
bot = Bot(token=token, parse_mode="HTML")
dp = Dispatcher()


@shared_task(base=BaseTask)
def tg_message_task(telegram_id, message):

    from .controllers.bot_services import tg_message

    loop = asyncio.get_event_loop()
    loop.run_until_complete(tg_message(bot, telegram_id, message))

    return True


@shared_task(base=BaseTask)
def save_client_task(name, surname, patronymic, person_fio, date_of_birth, phone_number, telegram_chat_id,
                     telegram_id, telegram_username, telegram_name, telegram_surname, email,
                     background_image, address, addition_information):

    from .controllers.bot_services import save_user

    save_user('Клиент', name, surname, patronymic, person_fio, date_of_birth, phone_number,
              telegram_chat_id, telegram_id, telegram_username, telegram_name, telegram_surname,
              email, background_image, address, addition_information)

    return True


@shared_task(base=BaseTask)
def request_api_car_info_task(message, telegram_id):

    from .controllers.bot_services import request_api_car_info

    request_api_car_info(message, telegram_id)

    return True

