import os
import logging
import json
import tempfile

import requests
import aiohttp
from django.db import transaction
from aiogram import types

from business_logic.models import *
from business_logic.controllers.utils import exist_user_check_status, tg_reminder, is_url, process_car_info, \
    make_api_request, handle_error_response

session = aiohttp.ClientSession()

logger = logging.getLogger('db_logger')
api_token = os.environ.get('API_TOKEN')
api_url = os.environ.get('API_URL')


def save_user(role_type=None, name=None, surname=None, patronymic=None, person_fio=None, date_of_birth=None,
              phone_number=None, telegram_chat_id=None, telegram_id=None, telegram_username=None, telegram_name=None,
              telegram_surname=None, email=None, background_image=None, address=None, addition_information=None):
    try:
        persons = exist_user_check_status(telegram_id, telegram_username)
        with transaction.atomic():
            if persons and persons.exists():
                try:
                    person = persons.last()
                    fields = {
                        'telegram_id': telegram_id, 'name': name, 'surname': surname, 'patronymic': patronymic,
                        'person_fio': person_fio, 'date_of_birth': date_of_birth, 'phone_number': phone_number,
                        'telegram_chat_id': telegram_chat_id, 'telegram_username': telegram_username,
                        'telegram_name': telegram_name, 'telegram_surname': telegram_surname, 'email': email,
                        'background_image': background_image
                    }

                    for field, value in fields.items():
                        if value:
                            setattr(person, field, value)

                    person.save()
                    logger.info(f'Задача - save_user для tg - {telegram_id} завершилась обновлением информации о '
                                f'пользователе')
                    return True

                except Exception as e:
                    logger.warning(f'Задача - save_user для tg - {telegram_id} должна была обновить информацию о '
                                   f'пользователе, но ошибка {e}')
                    return False
            else:
                role = Role.objects.filter(role_type=str(role_type)).last()
                if not role:
                    logger.warning(f'Задача - save_user для tg - {telegram_id}, '
                                   f'ошибка - не найдена роль - {role_type}')
                    return False

                try:
                    new_user = Person.objects.create(name=name, surname=surname, patronymic=patronymic,
                                                     date_of_birth=date_of_birth, phone_number=phone_number,
                                                     telegram_chat_id=telegram_chat_id,
                                                     telegram_id=telegram_id, telegram_username=telegram_username,
                                                     telegram_name=telegram_name, telegram_surname=telegram_surname,
                                                     email=email, background_image=background_image)
                    new_user.save()
                    new_user.role.add(role)
                    logger.info(f'Задача - save_user для tg - {telegram_id} завершилась созданием нового пользователя')
                    return True

                except Exception as e:
                    logger.warning(f'Задача - save_user для tg - {telegram_id} должна была создать его, но в поиске '
                                   f'заданной роли ошибка - {e}')
                    return False

    except Exception as e:
        logger.warning(f'Задача - save_user для tg - {telegram_id}, ошибка - {e}')
        return False


def request_api_car_info(message, telegram_id):
    headers = {"Authorization": f"Token {api_token}"}
    task_type = 'request_api_car_info'

    if is_url(message):
        api_type = "by_url"
        params = {"car_url": message}
        url = f'{api_url}/car_info/by_url/'
        response = make_api_request(url, params, headers, telegram_id, task_type)
    else:
        api_type = "by_vin"
        params = {"car_vin": message}
        url = f'{api_url}/car_info/by_vin/'
        response = make_api_request(url, params, headers, telegram_id, task_type)

    if not response:
        return False

    if response.status_code != 200:
        handle_error_response(telegram_id, task_type, api_type, response, message)
        return True

    process_car_info(telegram_id, response.json(), api_type)
    return True


# async def tg_message(bot, telegram_id, content, messages=None):
#     try:
#         async with session:
#             await bot.send_message(chat_id=telegram_id, text=content, parse_mode='HTML')
#             if messages:
#                 for msg in messages:
#                     await bot.delete_message(chat_id=telegram_id, message_id=msg)
#             return True
#     except Exception as e:
#         logger.warning(f'Задача - tg_message для tg - {telegram_id}, ошибка при отправке сообщения {e}')
#         return False


async def tg_message(bot, telegram_id, content, messages=None):
    try:
        async with session:
            content_json = json.dumps(content, indent=4)

            # Создаем временный файл и записываем туда JSON-строку
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content_json)

            # Отправляем файл пользователю в Telegram
            await bot.send_document(chat_id=telegram_id, document=types.FSInputFile(temp_file.name,
                                                                                      filename="Информация"))

            if messages:
                for msg in messages:
                    await bot.delete_message(chat_id=telegram_id, message_id=msg)

            return True
    except Exception as e:
        logger.warning(f'Задача - tg_message для tg - {telegram_id}, ошибка при отправке сообщения {e}')
        return False

