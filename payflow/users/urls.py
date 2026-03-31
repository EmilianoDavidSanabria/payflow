from django.urls import path

from .views import UserRegisterView, CurrentUserView, UserSearchView

urlpatterns = [
    path("register/", UserRegisterView.as_view()),
    path("me/", CurrentUserView.as_view()),
    path("search/", UserSearchView.as_view()),
]