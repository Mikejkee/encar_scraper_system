from django.core.management.base import BaseCommand
from business_logic.models import Role


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Role.objects.get_or_create(role_type='Клиент')
        self.stdout.write(self.style.SUCCESS('Successfully created role "Клиент"'))
