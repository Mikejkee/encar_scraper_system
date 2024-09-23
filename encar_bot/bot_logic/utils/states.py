from aiogram.fsm.state import StatesGroup, State


class RequestCarState(StatesGroup):
    request_car = State()
    action_type = State()
    request_analytic_type = State()


class RequestFilterState(StatesGroup):
    action_type = State()
    delete_filter = State()
    request_title_filter = State()
    request_link_filter = State()
    request_brand_filter = State()
    request_model_filter = State()
    request_generation_filter = State()
