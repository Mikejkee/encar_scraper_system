import os
import logging

import aiogram
import aiohttp
from django.db import transaction
from aiogram import types

from business_logic.telegram_tasks import tg_message_task
from business_logic.models import *
from business_logic.controllers.utils import exist_user_check_status, is_url, make_api_request, handle_error_response

session = aiohttp.ClientSession()

logger = logging.getLogger('db_logger')
api_url = os.environ.get('API_URL')
headers = {"Authorization": f"Token {os.environ.get('API_TOKEN')}"}


def save_user(role_type: str = None, name: str = None, surname: str = None, patronymic: str = None,
              person_fio: str = None, date_of_birth: str = None, phone_number: str = None, telegram_chat_id: str = None,
              telegram_id: str = None, telegram_username: str = None, telegram_name: str = None,
              telegram_surname: str = None, email: str = None, background_image: str = None) -> bool:
    try:
        persons = exist_user_check_status(telegram_id, telegram_username)
        with transaction.atomic():
            if persons:
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
                    logger.error(f'Задача - save_user для tg - {telegram_id} должна была обновить информацию о '
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
                    logger.error(f'Задача - save_user для tg - {telegram_id} должна была создать его, но в поиске '
                                 f'заданной роли ошибка - {e}')
                    return False

    except Exception as e:
        logger.error(f'Задача - save_user для tg - {telegram_id}, ошибка - {e}')
        return False


async def tg_message(bot: aiogram.Bot, telegram_id: str, file_path: str = None, message: str = None) -> bool:
    try:
        async with session:
            if file_path:
                filename = file_path.split(os.sep)[-1]
                await bot.send_document(chat_id=telegram_id, document=types.FSInputFile(file_path, filename=filename))
            else:
                await bot.send_message(chat_id=telegram_id, text=message)
            return True
    except Exception as e:
        logger.error(f'Задача - tg_message для tg - {telegram_id}, ошибка при отправке сообщения {e}')
        return False


def api_request_car_info(message: str, telegram_id: str) -> bool:
    task_type = 'api_request_car_info'

    if is_url(message):
        api_type = "by_url"
    else:
        api_type = "by_vin"

    params = {"car_url": message}
    url = f'{api_url}/car/info/{api_type}/'
    response = make_api_request(url, params, headers, telegram_id, task_type)

    if not response:
        return False

    car_info = response.json()
    message_formatted = f"""
            Идентификатор машины: {car_info['car_id']}
            Модель: {car_info['model']} 
            Марка: {car_info['brand']} 
            Год выпуска: {car_info['model_year']} 
            Пробег: {car_info['mileage']}
            Топливо: {car_info['fuel']}
            Ссылка: {car_info['link']}
            Ссылка на диагностику: {car_info['encar_diagnosis_url']} 
            Ссылка на страховку: {car_info['perfomance_record_url']} 
        """
    tg_message_task.apply_async(kwargs={'telegram_id': telegram_id, 'message': message_formatted}, countdown=0)
    return True


def api_request_filters(telegram_id: str) -> bool:
    task_type = 'api_request_filters'
    params = {"telegram_id": telegram_id}
    url = f'{api_url}/filter/info/'
    response = make_api_request(url, params, headers, telegram_id, task_type)

    if not response:
        return False

    filters_info = response.json()
    if len(filters_info) > 0:
        message_formatted = "\n".join([fr"ID - <b>{filter['id']} </b> ({filter['title']})" for filter in filters_info])
    else:
        message_formatted = "У вас нет выставленных фильтров"

    tg_message_task.apply_async(kwargs={'telegram_id': telegram_id, 'message': message_formatted}, countdown=0)
    return True


def api_delete_filter(telegram_id: str, filter_id: str) -> bool:
    task_type = 'api_delete_filter'
    params = {"telegram_id": telegram_id, 'filter_id': filter_id}
    url = f'{api_url}/filter/delete/'
    response = make_api_request(url, params, headers, telegram_id, task_type)

    if not response:
        return False

    message_formatted = "Фильтр успешно удален"
    tg_message_task.apply_async(kwargs={'telegram_id': telegram_id, 'message': message_formatted}, countdown=0)
    return True


def api_create_filter(telegram_id: str, title: str, link: str, brand: str, model: str, generation: str) -> bool:
    task_type = 'api_create_filter'
    params = {"telegram_id": telegram_id, 'title': title, 'link': link, "brand_code": brand, "model_code": model,
              "generation_code": generation}
    url = f'{api_url}/filter/create/'
    response = make_api_request(url, params, headers, telegram_id, task_type)

    if not response:
        return False

    message_formatted = "Фильтр успешно создан"
    tg_message_task.apply_async(kwargs={'telegram_id': telegram_id, 'message': message_formatted}, countdown=0)
    return True
