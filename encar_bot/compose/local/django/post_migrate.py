import os
import logging

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mainmodule.settings")
django.setup()

from business_logic.models import Role

logger = logging.getLogger('db_logger')


def create_client_role():
    try:
        Role.objects.get(role_type='Клиент')
        logger.info("Роль 'Клиент' уже существует.")
    except Role.DoesNotExist:
        Role.objects.create(role_type='Клиент')
        logger.info("Роль 'Клиент' успешно создана.")


if __name__ == '__main__':
    create_client_role()
