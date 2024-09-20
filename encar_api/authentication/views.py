from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from . import serializers
from .models import Person

User = get_user_model()


class PersonRegistrationAPIView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PersonRegistrationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh_token = RefreshToken.for_user(user)
        access_token = AccessToken.for_user(user)
        data = serializer.data
        data["tokens"] = {"refresh": str(refresh_token), "access": str(access_token)}

        return Response(data, status=status.HTTP_201_CREATED)


class PersonLoginAPIView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PersonLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        serializer = serializers.PersonSerializer(user)
        refresh_token = RefreshToken.for_user(user)
        access_token = AccessToken.for_user(user)
        data = serializer.data
        data["tokens"] = {"refresh": str(refresh_token), "access": str(access_token)}

        return Response(data, status=status.HTTP_200_OK)


class UserLogoutAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        try:
            data_refresh_token = request.data["refresh"]
            RefreshToken(data_refresh_token).blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)

        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)


class UserAPIView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.PersonSerializer

    def get_object(self):
        return self.request.user
