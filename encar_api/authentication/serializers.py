import os
import hashlib

from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate

from .models import *

User = get_user_model()


class PatchModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        kwargs['partial'] = True
        super(PatchModelSerializer, self).__init__(*args, **kwargs)


class PersonSerializer(serializers.ModelSerializer):

    class Meta:
        model = Person
        fields = ("id", "telegram_id")


class PersonRegistrationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Person
        fields = ("telegram_id",)

    def create(self, validated_data):
        return Person.objects.create_user(**validated_data)


class PersonLoginSerializer(serializers.Serializer):
    telegram_id = serializers.CharField()
    password = serializers.CharField(required=False)

    def validate(self, data):
        telegram_id = data.get('telegram_id')
        secret_key = os.environ.get('SECRET_KEY')
        password_string = f"{secret_key}{telegram_id}"
        user = authenticate(telegram_id=telegram_id, password=password_string)

        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect Credentials")


#
# class RoleSerializer(PatchModelSerializer):
#
#     class Meta:
#         model = Role
#         fields = ['role_type']
#
#
# class PersonSerializer(PatchModelSerializer):
#     role = RoleSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = Person
#         fields = ['telegram_id']
#
#
# class AdministratorSerializer(PatchModelSerializer):
#     role = RoleSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = Administrator
#         fields = '__all__'
#
#
# class ClientSerializer(PatchModelSerializer):
#     role = RoleSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = Client
#         fields = '__all__'
#
#
# class TokenSerializer(TokenObtainPairSerializer):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['password'].required = False
#
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)
#
#         token['telegram_id'] = user.telegram_id
#
#         return token

