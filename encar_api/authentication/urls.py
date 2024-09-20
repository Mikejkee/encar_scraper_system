from django.urls import path
from authentication import views
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("register/", views.PersonRegistrationAPIView.as_view(), name="create-user"),
    path("login/", views.PersonLoginAPIView.as_view(), name="login-user"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", views.UserLogoutAPIView.as_view(), name="logout-user"),
    path("", views.UserAPIView.as_view(), name="user-info"),
]