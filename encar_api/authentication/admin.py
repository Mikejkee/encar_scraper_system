from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

from django import forms


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", )


admin.site.register(Role)
admin.site.register(Person)
admin.site.register(Administrator)
