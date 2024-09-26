import os
import hashlib

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        validated_token = self.get_validated_token(raw_token)

        user = self.get_user(validated_token)

        telegram_id = request.data.get('telegram_id')
        if not telegram_id:
            raise AuthenticationFailed('telegram_id is required for authentication')

        return user, validated_token


class CustomUserManager(BaseUserManager):
    def create_user(self, telegram_id, **extra_fields):
        if not telegram_id:
            raise ValueError('Telegram ID is required')

        user = self.model(telegram_id=telegram_id, **extra_fields)
        user.set_password(None)

        user.save(using=self._db)
        return user

    def create_superuser(self, telegram_id, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(telegram_id, **extra_fields)


class Registrator(models.Model):
    creation_datetime = models.DateTimeField("Время создания", auto_now_add=True)
    update_datetime = models.DateTimeField("Время обновления", auto_now_add=True)
    flag = models.BooleanField("Флаг активности", default=1)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['creation_datetime'], name='index_%(class)s_time'),
        ]


class Role(Registrator):
    # Роль каждого пользователя
    role_type = models.CharField("Роль", max_length=50, null=True, blank=True)

    def __str__(self):
        return self.role_type

    class Meta:
        db_table = 'role'
        indexes = [] + Registrator.Meta.indexes


class Person(Registrator, AbstractBaseUser):
    # Класс человека, от которого будут наследоваться любые типы учетных записей в боте
    telegram_id = models.CharField("ID Телеграмм", max_length=20, null=True, blank=True, unique=True)
    person_fio = models.CharField("ФИО", max_length=200, null=True, blank=True)
    date_of_birth = models.DateField("Дата рождения", null=True, blank=True)
    phone_number = models.CharField("Номер телефона", max_length=12, null=True, blank=True)
    telegram_chat_id = models.CharField('ID Чата', max_length=255, null=True, blank=True)
    telegram_username = models.CharField("Username аккаунта Телеграмм", max_length=20, null=True, blank=True)
    telegram_name = models.CharField("Имя пользователя Телеграмм", max_length=20, null=True, blank=True)
    telegram_surname = models.CharField("Фамилия пользователя Телеграмм", max_length=20, null=True, blank=True)
    background_image = models.ImageField('Аватар пользователя ',
                                         upload_to='./postgres_data/objects/persons/background/', null=True,
                                         blank=True)

    role = models.ManyToManyField(Role, blank=True, related_name='roles', verbose_name="Роли")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()
    USERNAME_FIELD = 'telegram_id'
    REQUIRED_FIELDS = []

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    def set_password(self, raw_password):
        secret_key = os.environ.get('SECRET_KEY')
        password_string = f"{secret_key}{self.telegram_id}"
        hash_object = hashlib.sha256(password_string.encode())
        hashed_password = hash_object.hexdigest()
        self.password = hashed_password

    def check_password(self, raw_password):
        hash_object = hashlib.sha256(raw_password.encode())
        hashed_raw_password = hash_object.hexdigest()
        return hashed_raw_password == self.password

    class Meta:
        db_table = 'person'
        indexes = [
                      models.Index(fields=['phone_number'],
                                   name='index_persons_phone_number'),
                      models.Index(fields=['telegram_id'],
                                   name='index_persons_telegram_id'),
                  ] + Registrator.Meta.indexes


class Administrator(Person):
    whom_created = models.CharField("Создатель", max_length=20, null=True, blank=True)
    addition_information = models.TextField("Дополнительная информация", null=True, blank=True)

    def __str__(self):
        if self.telegram_username:
            return self.telegram_username
        elif self.telegram_id:
            return self.telegram_id
        else:
            return str(self.id)

    class Meta:
        db_table = 'administrator'


class Client(Person):
    addition_information = models.TextField("Дополнительная информация", null=True, blank=True)

    def __str__(self):
        if self.telegram_username:
            return self.telegram_username
        else:
            return self.telegram_id

    class Meta:
        db_table = 'client'
