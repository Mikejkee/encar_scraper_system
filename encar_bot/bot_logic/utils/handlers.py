import logging

from aiogram.types import Message
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot_logic.utils.states import RequestCarState
from bot_logic.utils.filters import TextAndFilter
from bot_logic.utils.additional_functions import (save_client, check_user_status, request_car, request_car_analytic,
                                                  request_car_insurance, request_car_diagnostic, request_analytic_cost,
                                                  request_analytic_damage)
from bot_logic.utils.keyboards import (start_menu_buttons, cars_menu_buttons, cars_analytic_menu_buttons,
                                       head_menu_button)

router = Router()
logger = logging.getLogger('db_logger')


@router.message(Command("start"))
async def start_menu(message: Message, state: FSMContext):
    await state.clear()

    chat = message.chat
    chat_id = chat.id
    from_user = message.from_user
    telegram_id = from_user.id
    telegram_username = from_user.username
    telegram_name = from_user.first_name
    telegram_surname = from_user.last_name

    await save_client(logger, telegram_chat_id=chat_id, telegram_id=telegram_id, telegram_name=telegram_name,
                      telegram_surname=telegram_surname, telegram_username=telegram_username)

    hello = f'Добро пожаловать в нашу систему!'
    if not await check_user_status(telegram_id):
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

    keyboard = await start_menu_buttons(telegram_id)

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
async def request_car(message: Message, state: FSMContext):
    keyboard = await head_menu_button()
    await message.answer(f'Пришлите ссылку на автомобиль в формате (encar.com/...&carid=00000000&...) или VIN',
                         reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(RequestCarState.request_car)


@router.message(RequestCarState.request_car)
async def car_menu(message: Message, state: FSMContext):
    # TODO: обработку машины тут сделать, чтобы левак не проходил уже на этом этапе
    from_user = message.from_user
    telegram_id = from_user.id
    await state.update_data(request_car=message.text, telegram_id=telegram_id)

    keyboard = await cars_menu_buttons()
    await message.answer(
        text="Машина принята, выберите дальнейшее действие",
        reply_markup=keyboard
    )
    await state.set_state(RequestCarState.action_type)


@router.message(RequestCarState.action_type, F.text("Карточка машины"))
async def request_car_info(message: Message, state: FSMContext):
    state_data = await state.get_data()
    telegram_id = state_data.get('telegram_id')
    car_id = state_data.get('request_car')

    keyboard = await cars_menu_buttons()
    chosen_state = RequestCarState.action_type
    answer_text = "Запрос принят, ожидайте ответа!"

    if message.text is "Аналитика машины":
        keyboard = await cars_analytic_menu_buttons()
        answer_text = 'Выберите желаемую аналитику'
        chosen_state = RequestCarState.request_analytic_type
    elif message.text is "Карточка машины":
        await request_car(logger, car_id, telegram_id)
    elif message.text is "Карточка страховки машины":
        await request_car_insurance(logger, car_id, telegram_id)
    elif message.text is "Карточка диагностики машины":
        await request_car_diagnostic(logger, car_id, telegram_id)

    await message.answer(text=answer_text, reply_markup=keyboard)
    await state.set_state(chosen_state)


@router.message(RequestCarState.request_analytic_type)
async def request_analytic(message: Message, state: FSMContext):
    state_data = await state.get_data()
    telegram_id = state_data.get('telegram_id')
    car_id = state_data.get('request_car')

    if message.text is "Аналитика стоимости машины":
        await request_analytic_cost(logger, car_id, telegram_id)
    elif message.text is "Аналитика повреждений":
        await request_analytic_damage(logger, car_id, telegram_id)

    keyboard = await cars_analytic_menu_buttons()
    await message.answer(
        text="Запрос принят, ожидайте ответа!",
        reply_markup=keyboard
    )
    await state.set_state(RequestCarState.request_analytic_type)


@router.message(F.text('Назад к информации о машине'))
async def back_car_menu(message: Message, state: FSMContext):
    keyboard = await cars_menu_buttons()

    await state.set_state(RequestCarState.action_type)
    await message.answer('Выберите необходимое', reply_markup=keyboard, parse_mode='HTML')


@router.message(F.text('🔙 Главное меню'))
async def head_menu(message: Message, state: FSMContext):
    from_user = message.from_user
    telegram_id = from_user.id
    keyboard = await start_menu_buttons(telegram_id)

    await state.clear()
    await message.answer('Выберите необходимое', reply_markup=keyboard, parse_mode='HTML')
