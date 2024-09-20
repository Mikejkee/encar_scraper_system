import os

from asgiref.sync import sync_to_async
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

ADMINS_LIST = os.environ.get('ADMINS_LIST').split(',')


@sync_to_async
def start_menu_buttons(user_telegram_id: int):
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

    # TODO: реализовать через запрос в бд
    if user_telegram_id in ADMINS_LIST:
        buttons.append([KeyboardButton(text='Администрирование бота')])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, input_field_placeholder="Воспользуйтесь меню:")


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
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, input_field_placeholder="Выберите пункт меню:")


@sync_to_async
def cars_menu_buttons():
    buttons = [
        [
            KeyboardButton(text='Карточка машины'),
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
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, input_field_placeholder="Выберите пункт меню:")


@sync_to_async
def cars_analytic_menu_buttons():
    buttons = [
        [
            KeyboardButton(text='Аналитика стоимости машины'),
            KeyboardButton(text='Аналитика повреждений'),
        ],
        [
            KeyboardButton(text='Назад к информации о машине'),
            KeyboardButton(text='🔙 Главное меню'),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, input_field_placeholder="Выберите пункт меню:")


@sync_to_async
def head_menu_button():
    buttons = [
        [
            KeyboardButton(text='🔙 Главное меню')
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, input_field_placeholder="Выберите пункт меню:")