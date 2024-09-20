from django.db import models
import hashlib
from datetime import datetime

from django.db import models


class Registrator(models.Model):
    creation_datetime = models.DateTimeField("Время создания", auto_now_add=True)
    update_datetime = models.DateTimeField("Время обновления", auto_now_add=True)
    flag = models.BooleanField("Флаг активности", default=1)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['creation_datetime'], name='index_%(class)s_time'),
        ]


class DBLog(Registrator):
    time = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10)
    message = models.TextField()
    filename = models.CharField(max_length=255)
    func_name = models.CharField(max_length=255)
    lineno = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        ordering = ['-time']
        verbose_name = "Log"
        verbose_name_plural = "Logs"

        db_table = 'db_log'
        indexes = [
            models.Index(fields=['time'],
                         name='ind_db_log_time'),
            models.Index(fields=['level'],
                         name='ind_db_log_level')
        ]

    def __str__(self):
        return f'{self.message}'


class Role(Registrator):
    role_type = models.CharField("Роль", max_length=50, null=True, blank=True)

    def __str__(self):
        return self.role_type

    class Meta:
        db_table = 'role'
        indexes = [] + Registrator.Meta.indexes


class Person(Registrator):
    name = models.CharField("Имя", max_length=20, null=True, blank=True)
    surname = models.CharField("Фамилия", max_length=20, null=True, blank=True)
    patronymic = models.CharField("Отчество", max_length=20, null=True, blank=True)
    date_of_birth = models.DateField("Дата рождения", null=True, blank=True)
    person_fio = models.CharField("ФИО", max_length=200, null=True, blank=True)
    phone_number = models.CharField("Номер телефона", max_length=12, null=True, blank=True)
    telegram_chat_id = models.CharField('ID Чата', max_length=255, null=True, blank=True)
    telegram_id = models.CharField("ID Телеграмм", max_length=20, null=True, blank=True)
    telegram_username = models.CharField("Username аккаунта Телеграмм", max_length=20, null=True, blank=True)
    telegram_name = models.CharField("Имя пользователя Телеграмм", max_length=20, null=True, blank=True)
    telegram_surname = models.CharField("Фамилия пользователя Телеграмм", max_length=20, null=True, blank=True)
    email = models.EmailField("Электронная почта", null=True, blank=True)
    background_image = models.ImageField('Аватар пользователя ',
                                         upload_to='./postgres_data/objects/persons/background/', null=True,
                                         blank=True)

    role = models.ManyToManyField(Role, blank=True, related_name='roles', verbose_name="Роли")

    class Meta:
        db_table = 'person'
        indexes = [
                      models.Index(fields=['phone_number'],
                                   name='index_persons_phone_number'),
                      models.Index(fields=['telegram_id'],
                                   name='index_persons_telegram_id'),
                      models.Index(fields=['email'],
                                   name='index_persons_email'),
                  ] + Registrator.Meta.indexes

