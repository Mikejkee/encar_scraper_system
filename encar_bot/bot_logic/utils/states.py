from aiogram.fsm.state import StatesGroup, State


class RequestCarState(StatesGroup):
    request_car = State()
    action_type = State()
    request_analytic_type = State()