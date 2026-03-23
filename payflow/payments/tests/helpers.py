from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


def create_user(username, password="pass", balance=None):
    user = User.objects.create_user(username=username, password=password)

    if balance is not None:
        user.wallet.balance = Decimal(balance)
        user.wallet.save(update_fields=["balance"])

    return user


def authenticate_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client