import os

# import django
from asgiref.sync import sync_to_async


# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mainmodule.settings")
# django.setup()

# from business_logic.telegram_tasks import save_client_task, request_api_car_info_task


@sync_to_async
def save_client(logger, name=None, surname=None, patronymic=None, person_fio=None,
                date_of_birth=None, phone_number=None, telegram_chat_id=None,
                telegram_id=None, telegram_username=None, telegram_name=None,
                telegram_surname=None, email=None, background_image=None, address=None,
                addition_information=None):
    # client_task = save_client_task.delay(name, surname, patronymic, person_fio, date_of_birth, phone_number,
    #                                      telegram_chat_id, telegram_id, telegram_username, telegram_name,
    #                                      telegram_surname, email, background_image, address,
    #                                      addition_information)

    logger.info(f'Задача создана - save_client_task, id - {"client_task.task_id"}')


@sync_to_async
def check_user_status(telegram_id):
    # Заглушка для реализации платной подписки
    return True


@sync_to_async
def request_car(logger, message, telegram_id):
    # request_car_task = request_api_car_info_task.delay(message, telegram_id)
    logger.info(f'Задача создана - request_api_car_info_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_car_insurance(logger, message, telegram_id):
    logger.info(f'Задача создана - request_api_car_insurance_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_car_diagnostic(logger, message, telegram_id):
    logger.info(f'Задача создана - request_api_car_diagnostic_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_car_analytic(logger, message, telegram_id):
    logger.info(f'Задача создана - request_api_car_analytic_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_analytic_cost(logger, message, telegram_id):
    logger.info(f'Задача создана - request_analytic_cost_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_analytic_damage(logger, message, telegram_id):
    logger.info(f'Задача создана - request_analytic_damage_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def request_filter(logger, telegram_id):
    logger.info(f'Задача создана - request_filter_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def create_filter(logger, telegram_id, title, link, brand, model, generation):
    logger.info(f'Задача создана - create_filter_task, id - {"request_car_task.task_id"}')
    return True


@sync_to_async
def delete_filter(logger, telegram_id, filter_id):
    logger.info(f'Задача создана - delete_filter_task, id - {"request_car_task.task_id"}')
    return True


