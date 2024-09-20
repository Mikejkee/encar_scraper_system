import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):

    def handle(self, *args, **options):
        telegram_id = os.environ.get('DJANGO_SUPERUSER_TELEGRAM')

        if not User.objects.filter(telegram_id=telegram_id).exists():
            print('Creating account for %s' % (telegram_id, ))
            admin = User.objects.create_superuser(telegram_id=telegram_id)
        else:
            print('Admin account has already been initialized.')