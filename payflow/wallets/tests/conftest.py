import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from wallets.models import Wallet

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def wallet_user():
    return User.objects.create_user(
        username="wallet_test_user",
        password="pass12345",
    )


@pytest.fixture
def authenticated_client(api_client, wallet_user):
    api_client.force_authenticate(wallet_user)
    return api_client


@pytest.fixture
def wallet(wallet_user):
    return wallet_user.wallet


@pytest.fixture
def funded_wallet(wallet):
    wallet.balance = Decimal("200.00")
    wallet.save(update_fields=["balance"])
    return wallet