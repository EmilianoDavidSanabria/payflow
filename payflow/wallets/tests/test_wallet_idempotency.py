import pytest
from decimal import Decimal

from django.urls import reverse

from wallets.models import WalletTransaction


@pytest.mark.django_db
def test_wallet_top_up_is_idempotent(authenticated_client, wallet):

    url = reverse("wallet-top-up")

    headers = {
        "HTTP_IDEMPOTENCY_KEY": "test-key-123"
    }

    response1 = authenticated_client.post(
        url,
        {"amount": "50.00"},
        format="json",
        **headers
    )

    response2 = authenticated_client.post(
        url,
        {"amount": "50.00"},
        format="json",
        **headers
    )

    wallet.refresh_from_db()

    assert response1.status_code == 201
    assert response2.status_code == 201

    assert response1.data == response2.data

    assert wallet.balance == Decimal("50.00")

    assert WalletTransaction.objects.count() == 1


@pytest.mark.django_db
def test_wallet_top_up_without_idempotency_key_creates_two_transactions(
    authenticated_client,
    wallet
):

    url = reverse("wallet-top-up")

    authenticated_client.post(
        url,
        {"amount": "30.00"},
        format="json",
    )

    authenticated_client.post(
        url,
        {"amount": "30.00"},
        format="json",
    )

    wallet.refresh_from_db()

    assert wallet.balance == Decimal("60.00")

    assert WalletTransaction.objects.count() == 2


@pytest.mark.django_db
def test_wallet_withdraw_is_idempotent(authenticated_client, funded_wallet):

    url = reverse("wallet-withdraw")

    headers = {
        "HTTP_IDEMPOTENCY_KEY": "withdraw-key-456"
    }

    response1 = authenticated_client.post(
        url,
        {"amount": "40.00"},
        format="json",
        **headers
    )

    response2 = authenticated_client.post(
        url,
        {"amount": "40.00"},
        format="json",
        **headers
    )

    funded_wallet.refresh_from_db()

    assert response1.status_code == 201
    assert response2.status_code == 201

    assert response1.data == response2.data

    assert funded_wallet.balance == Decimal("160.00")

    assert WalletTransaction.objects.count() == 1