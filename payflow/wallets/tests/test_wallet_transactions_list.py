import pytest
from decimal import Decimal
from django.urls import reverse

from wallets.models import WalletTransaction


@pytest.mark.django_db
def test_wallet_transactions_list_returns_only_authenticated_user_transactions(
    authenticated_client,
    wallet,
):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("30.00"),
        status="COMPLETED",
        rail="SANDBOX",
        provider_status="COMPLETED",
    )

    response = authenticated_client.get(reverse("wallet-transactions"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["transaction_type"] == "TOP_UP"


@pytest.mark.django_db
def test_wallet_transactions_list_filters_by_type(authenticated_client, wallet):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("60.00"),
        status="COMPLETED",
        rail="SANDBOX",
        provider_status="COMPLETED",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="WITHDRAWAL",
        amount=Decimal("10.00"),
        status="COMPLETED",
        rail="SANDBOX",
        provider_status="COMPLETED",
    )

    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {"type": "TOP_UP"},
    )

    assert response.status_code == 200
    assert response.data["type"] == "TOP_UP"
    assert response.data["count"] == 1
    assert response.data["results"][0]["transaction_type"] == "TOP_UP"


@pytest.mark.django_db
def test_wallet_transactions_list_filters_by_status(authenticated_client, wallet):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("20.00"),
        status="COMPLETED",
        rail="SANDBOX",
        provider_status="COMPLETED",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="WITHDRAWAL",
        amount=Decimal("15.00"),
        status="FAILED",
        rail="SANDBOX",
        provider_status="FAILED",
    )

    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {"status": "FAILED"},
    )

    assert response.status_code == 200
    assert response.data["status"] == "FAILED"
    assert response.data["count"] == 1
    assert response.data["results"][0]["status"] == "FAILED"


@pytest.mark.django_db
def test_wallet_transactions_list_rejects_invalid_type(authenticated_client):
    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {"type": "SOMETHING_ELSE"},
    )

    assert response.status_code == 400
    assert response.data["error"] == "type must be one of: all, TOP_UP, WITHDRAWAL"


@pytest.mark.django_db
def test_wallet_transactions_list_rejects_invalid_status(authenticated_client):
    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {"status": "UNKNOWN"},
    )

    assert response.status_code == 400
    assert response.data["error"] == "status must be one of: all, PENDING, COMPLETED, FAILED"


@pytest.mark.django_db
def test_wallet_transactions_list_contract_has_expected_keys(authenticated_client, wallet):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("55.00"),
        status="COMPLETED",
        rail="SANDBOX",
        provider_status="COMPLETED",
    )

    response = authenticated_client.get(reverse("wallet-transactions"))

    assert response.status_code == 200
    assert set(response.data.keys()) == {
        "count",
        "page",
        "page_size",
        "total_pages",
        "type",
        "status",
        "rail",
        "provider_status",
        "results",
    }

    assert set(response.data["results"][0].keys()) == {
        "id",
        "wallet_id",
        "transaction_type",
        "amount",
        "status",
        "rail",
        "external_reference",
        "provider_status",
        "checkout_url",
        "failure_reason",
        "created_at",
        "updated_at",
        "completed_at",
    }


@pytest.mark.django_db
def test_wallet_transactions_list_requires_authentication(api_client):
    response = api_client.get(reverse("wallet-transactions"))

    assert response.status_code == 401