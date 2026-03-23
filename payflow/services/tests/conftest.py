import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from wallets.models import Wallet


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def wallet_user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="service_test_user",
        password="testpass123",
    )


@pytest.fixture
def wallet(db, wallet_user):
    return Wallet.objects.get(user=wallet_user)


@pytest.fixture
def funded_wallet(db, wallet):
    wallet.balance = Decimal("200.00")
    wallet.save(update_fields=["balance", "updated_at"])
    return wallet


@pytest.fixture
def authenticated_client(db, api_client, wallet_user):
    api_client.force_authenticate(user=wallet_user)
    return api_client