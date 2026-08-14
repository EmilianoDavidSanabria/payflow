from django.urls import path

from .views import (
    UserRegisterView,
    CurrentUserView,
    UserSearchView,
    ChangePasswordView,
)

urlpatterns = [
    path("register/", UserRegisterView.as_view()),
    path("me/", CurrentUserView.as_view()),
    path("search/", UserSearchView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
]