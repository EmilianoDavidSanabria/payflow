import pytest
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from wallets.models import WalletTransaction


@pytest.mark.django_db
@patch("wallets.funding_views.PaymentReconciliationService")
def test_refresh_status_completes_transaction(
    reconciliation_mock,
    authenticated_client,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("100.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="123",
    )

    tx.status = "COMPLETED"
    reconciliation_mock.refresh_topup_status.return_value = tx

    response = authenticated_client.post(
        reverse("wallet-transaction-refresh-status", args=[tx.id])
    )

    assert response.status_code == 200
    assert response.data["status"] == "COMPLETED"


@pytest.mark.django_db
@patch("wallets.funding_views.PaymentReconciliationService")
def test_refresh_status_fails_transaction(
    reconciliation_mock,
    authenticated_client,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("50.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="456",
    )

    tx.status = "FAILED"
    tx.failure_reason = "rejected"

    reconciliation_mock.refresh_topup_status.return_value = tx

    response = authenticated_client.post(
        reverse("wallet-transaction-refresh-status", args=[tx.id])
    )

    assert response.status_code == 200
    assert response.data["status"] == "FAILED"
    assert response.data["failure_reason"] == "rejected"


@pytest.mark.django_db
@patch("wallets.funding_views.PaymentReconciliationService")
def test_refresh_status_keeps_pending_if_no_change(
    reconciliation_mock,
    authenticated_client,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("70.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="789",
        provider_status="pending",
    )

    reconciliation_mock.refresh_topup_status.return_value = tx

    response = authenticated_client.post(
        reverse("wallet-transaction-refresh-status", args=[tx.id])
    )

    assert response.status_code == 200
    assert response.data["status"] == "PENDING"


@pytest.mark.django_db
def test_refresh_status_rejects_non_topup(authenticated_client, wallet):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="WITHDRAWAL",
        amount=Decimal("30.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
    )

    response = authenticated_client.post(
        reverse("wallet-transaction-refresh-status", args=[tx.id])
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_refresh_status_rejects_non_mercadopago(authenticated_client, wallet):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("30.00"),
        status="PENDING",
        rail="SANDBOX",
    )

    response = authenticated_client.post(
        reverse("wallet-transaction-refresh-status", args=[tx.id])
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_refresh_status_returns_404_if_not_found(authenticated_client):
    response = authenticated_client.post(
        reverse("wallet-transaction-refresh-status", args=[999999])
    )

    assert response.status_code == 404