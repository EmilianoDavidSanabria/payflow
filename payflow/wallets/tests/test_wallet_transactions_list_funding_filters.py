import pytest
from decimal import Decimal
from django.urls import reverse

from wallets.models import WalletTransaction


@pytest.mark.django_db
def test_wallet_transactions_list_filters_by_rail(authenticated_client, wallet):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("100.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        provider_status="CHECKOUT_CREATED",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("40.00"),
        status="COMPLETED",
        rail="SANDBOX",
        provider_status="COMPLETED",
    )

    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {"rail": "MERCADO_PAGO"},
    )

    assert response.status_code == 200
    assert response.data["rail"] == "MERCADO_PAGO"
    assert response.data["count"] == 1
    assert response.data["results"][0]["rail"] == "MERCADO_PAGO"


@pytest.mark.django_db
def test_wallet_transactions_list_filters_by_provider_status(authenticated_client, wallet):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("120.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        provider_status="CHECKOUT_CREATED",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("75.00"),
        status="FAILED",
        rail="MERCADO_PAGO",
        provider_status="rejected",
    )

    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {"provider_status": "CHECKOUT_CREATED"},
    )

    assert response.status_code == 200
    assert response.data["provider_status"] == "CHECKOUT_CREATED"
    assert response.data["count"] == 1
    assert response.data["results"][0]["provider_status"] == "CHECKOUT_CREATED"


@pytest.mark.django_db
def test_wallet_transactions_list_rejects_invalid_rail(authenticated_client):
    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {"rail": "CRYPTO_MAGIC"},
    )

    assert response.status_code == 400
    assert response.data["error"] == (
        "rail must be one of: all, SANDBOX, BANK_TRANSFER, CARD, MERCADO_PAGO"
    )


@pytest.mark.django_db
def test_wallet_transactions_list_combines_status_and_rail_filters(authenticated_client, wallet):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("80.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        provider_status="CHECKOUT_CREATED",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("80.00"),
        status="COMPLETED",
        rail="MERCADO_PAGO",
        provider_status="approved",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("80.00"),
        status="PENDING",
        rail="SANDBOX",
        provider_status="PENDING",
    )

    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {
            "status": "PENDING",
            "rail": "MERCADO_PAGO",
        },
    )

    assert response.status_code == 200
    assert response.data["status"] == "PENDING"
    assert response.data["rail"] == "MERCADO_PAGO"
    assert response.data["count"] == 1

    result = response.data["results"][0]
    assert result["status"] == "PENDING"
    assert result["rail"] == "MERCADO_PAGO"


@pytest.mark.django_db
def test_wallet_transactions_list_combines_provider_status_and_rail_filters(
    authenticated_client,
    wallet,
):
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("150.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        provider_status="CHECKOUT_CREATED",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("150.00"),
        status="PENDING",
        rail="CARD",
        provider_status="CHECKOUT_CREATED",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("150.00"),
        status="FAILED",
        rail="MERCADO_PAGO",
        provider_status="rejected",
    )

    response = authenticated_client.get(
        reverse("wallet-transactions"),
        {
            "provider_status": "CHECKOUT_CREATED",
            "rail": "MERCADO_PAGO",
        },
    )

    assert response.status_code == 200
    assert response.data["provider_status"] == "CHECKOUT_CREATED"
    assert response.data["rail"] == "MERCADO_PAGO"
    assert response.data["count"] == 1

    result = response.data["results"][0]
    assert result["provider_status"] == "CHECKOUT_CREATED"
    assert result["rail"] == "MERCADO_PAGO"