import os
import logging

import asyncio
import django
from asgiref.sync import sync_to_async
from aiogram import F, Bot, Dispatcher, types, Router
from aiogram.filters import BaseFilter
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters.command import Command
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mainmodule.settings")
django.setup()

from business_logic.telegram_tasks import save_client_task, request_api_car_info_task
from business_logic.controllers.utils import is_url

# Логирование
logger = logging.getLogger('db_logger')

TOKEN = os.environ.get('TELEGRAM_TOKEN')
router = Router()
storage = RedisStorage.from_url(os.environ.get('CELERY_BACKEND'))


class TextAndFilter(BaseFilter):
    def __init__(self, values):
        self.values = values

    async def __call__(self, message: types.Message):
        return message.text in self.values


@sync_to_async
def save_client(name=None, surname=None, patronymic=None, person_fio=None,
                date_of_birth=None, phone_number=None, telegram_chat_id=None,
                telegram_id=None, telegram_username=None, telegram_name=None,
                telegram_surname=None, email=None, background_image=None, address=None,
                addition_information=None):
    client_task = save_client_task.delay(name, surname, patronymic, person_fio, date_of_birth, phone_number,
                                         telegram_chat_id, telegram_id, telegram_username, telegram_name,
                                         telegram_surname, email, background_image, address,
                                         addition_information)

    logger.info(f'Задача создана - save_client_task, id - {client_task.task_id}')


@sync_to_async
def check_user_exist(telegram_id):
    # Заглушка для реализации платной подписки
    return True


@sync_to_async
def request_car_from_message(message, telegram_id):
    request_car_task = request_api_car_info_task.delay(message, telegram_id)
    logger.info(f'Задача создана - request_api_car_info_task, id - {request_car_task.task_id}')


@sync_to_async
def start_menu_buttons():
    buttons = [
        [
            KeyboardButton(text='Активные фильтры'),
            KeyboardButton(text='Информация о машине'),
        ],
        [
            KeyboardButton(text='Баланс/подписка'),
            KeyboardButton(text='О системе'),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@sync_to_async
def filter_menu_buttons():
    buttons = [
        [
            KeyboardButton(text='Просмотр фильтров'),
            KeyboardButton(text='Добавить новый фильтр'),
        ],
        [
            KeyboardButton(text='Удалить фильтр'),
            KeyboardButton(text='🔙 Главное меню'),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@sync_to_async
def cars_menu_buttons():
    buttons = [
        [
            KeyboardButton(text='Карточка машины по ссылке или VIN'),
            KeyboardButton(text='Аналитика машины'),
        ],
        [
            KeyboardButton(text='Карточка страховки машины'),
            KeyboardButton(text='Карточка диагностики машины'),
        ],
        [
            KeyboardButton(text='🔙 Главное меню'),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@sync_to_async
def cars_analytic_menu_buttons():
    buttons = [
        [
            KeyboardButton(text='Аналитика стоимости машины'),
            KeyboardButton(text='Аналитика повреждений'),
        ],
        [
            KeyboardButton(text='🔙 Главное меню'),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@sync_to_async
def head_menu_button():
    buttons = [
        [
            KeyboardButton(text='🔙 Главное меню')
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


class RequestCarState(StatesGroup):
    request_car = State()


class RequestCarState(StatesGroup):
    request_car = State()


@router.message(F.text, Command("start"))
async def start_menu(message: Message, state: FSMContext):
    await state.clear()

    chat = message.chat
    chat_id = chat.id
    from_user = message.from_user
    telegram_id = from_user.id
    telegram_username = from_user.username
    telegram_name = from_user.first_name
    telegram_surname = from_user.last_name

    await save_client(telegram_chat_id=chat_id, telegram_id=telegram_id, telegram_name=telegram_name,
                      telegram_surname=telegram_surname, telegram_username=telegram_username)

    hello = f'Добро пожаловать в нашу систему!'
    if not await check_user_exist(telegram_id):
        await message.answer(f'{hello}\n\n'
                             f'Обратитесь к администратору для получения доступа!',
                             parse_mode='HTML')

    if not telegram_username:
        if telegram_name:
            hello = f'<b>{telegram_name}</b>, приветствуем тебя!'
        elif not telegram_name and telegram_surname:
            hello = f'<b>{telegram_surname}</b>, приветствуем тебя!'
    else:
        hello = f'<b>{telegram_username}</b>, приветствуем тебя!'

    keyboard = await start_menu_buttons()

    await message.answer(f'{hello}\n\n'
                         'Encar System - помощник для отслеживания корейских машин с сайта Encar.\n\n'
                         'Вы можете начать отслеживать фильтр поиска машины, получить информацию о конкретной машине, '
                         'ее страховке и диагностике.\n\n'
                         'Бот будет сообщать вам информацию о новых машинах, доступных по поиску\n\n'
                         '\n\n'
                         'Покупайте подписку и пользуйтесь всеми возможностями системы!',
                         reply_markup=keyboard,
                         parse_mode='HTML')


@router.message(TextAndFilter(values={"Информация о машине", "/car"}))
async def cars_menu(message: Message):
    keyboard = await cars_menu_buttons()
    await message.answer(f'Выберите необходимый пункт из меню',
                         reply_markup=keyboard, parse_mode='HTML')


@router.message(F.text("Карточка машины по ссылке или VIN"))
async def request_car_info(message: Message, state: FSMContext):
    keyboard = await cars_menu_buttons()
    await message.answer(f'Пришлите ссылку на автомобиль в формате (encar.com/...&carid=00000000&...) или VIN',
                         reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(RequestCarState.request_car)


@router.message(F.text("Аналитика машины"))
async def request_car_info(message: Message, state: FSMContext):
    keyboard = await cars_analytic_menu_buttons()
    await message.answer(f'Пришлите ссылку на автомобиль в формате (encar.com/...&carid=00000000&...) или VIN',
                         reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(RequestCarState.request_car)


@router.message(RequestCarState.request_car)
async def request_car_info_response(message: Message, state: FSMContext):
    from_user = message.from_user
    telegram_id = from_user.id

    await request_car_from_message(message.text, telegram_id)

    keyboard = await start_menu_buttons()
    await message.answer(
        text="Запрос принят, ожидайте ответа!",
        reply_markup=keyboard
    )
    await state.clear()


@router.message(F.text('🔙 Главное меню'))
async def head_menu(message: Message, state: FSMContext):
    keyboard = await start_menu_buttons()

    await state.clear()
    await message.answer('Выберите необходимое',
                         reply_markup=keyboard,
                         parse_mode='HTML')


async def main():
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
