import pytest
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse

from audit.models import AuditLog
from ledger.models import LedgerEntry
from wallets.models import WalletTransaction


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_intent_creates_pending_transaction_without_updating_balance(
    mercado_pago_service_mock,
    authenticated_client,
    wallet,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/intent-123",
        "provider_reference": "pref_123",
    }

    response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "120.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    wallet.refresh_from_db()

    assert response.status_code == 201
    assert response.data["transaction_type"] == "TOP_UP"
    assert response.data["status"] == "PENDING"
    assert response.data["rail"] == "MERCADO_PAGO"
    assert response.data["provider_status"] == "CHECKOUT_CREATED"
    assert response.data["external_reference"] == str(response.data["id"])
    assert response.data["checkout_url"] == "https://mp.test/checkout/intent-123"
    assert wallet.balance == Decimal("0.00")


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_complete_webhook_completes_transaction_and_updates_balance(
    mercado_pago_service_mock,
    authenticated_client,
    wallet,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/complete-123",
        "provider_reference": "pref_456",
    }

    create_response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "90.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    transaction_id = create_response.data["id"]

    webhook_response = authenticated_client.post(
        reverse("wallet-top-up-webhook-complete", kwargs={"transaction_id": transaction_id}),
        {
            "external_reference": "mp-payment-123",
            "provider_status": "APPROVED",
        },
        format="json",
        HTTP_X_WEBHOOK_SECRET=settings.PAYFLOW_WEBHOOK_SECRET,
    )

    wallet.refresh_from_db()

    assert webhook_response.status_code == 200
    assert webhook_response.data["status"] == "COMPLETED"
    assert webhook_response.data["provider_status"] == "APPROVED"
    assert webhook_response.data["external_reference"] == "mp-payment-123"
    assert wallet.balance == Decimal("90.00")

    reference = f"wallet_transaction_{transaction_id}"
    entries = LedgerEntry.objects.filter(reference=reference)

    assert entries.count() == 2
    assert sum(entry.debit for entry in entries) == Decimal("90.00")
    assert sum(entry.credit for entry in entries) == Decimal("90.00")


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_complete_webhook_is_idempotent_for_completed_transaction(
    mercado_pago_service_mock,
    authenticated_client,
    wallet,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/idempotent-123",
        "provider_reference": "pref_789",
    }

    create_response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "55.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    transaction_id = create_response.data["id"]

    first_response = authenticated_client.post(
        reverse("wallet-top-up-webhook-complete", kwargs={"transaction_id": transaction_id}),
        {
            "external_reference": "mp-payment-456",
            "provider_status": "APPROVED",
        },
        format="json",
        HTTP_X_WEBHOOK_SECRET=settings.PAYFLOW_WEBHOOK_SECRET,
    )

    second_response = authenticated_client.post(
        reverse("wallet-top-up-webhook-complete", kwargs={"transaction_id": transaction_id}),
        {
            "external_reference": "mp-payment-456",
            "provider_status": "APPROVED",
        },
        format="json",
        HTTP_X_WEBHOOK_SECRET=settings.PAYFLOW_WEBHOOK_SECRET,
    )

    wallet.refresh_from_db()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert wallet.balance == Decimal("55.00")

    reference = f"wallet_transaction_{transaction_id}"
    entries = LedgerEntry.objects.filter(reference=reference)

    assert entries.count() == 2


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_fail_webhook_marks_transaction_as_failed_without_updating_balance(
    mercado_pago_service_mock,
    authenticated_client,
    wallet,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/fail-123",
        "provider_reference": "pref_fail_123",
    }

    create_response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "70.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    transaction_id = create_response.data["id"]

    webhook_response = authenticated_client.post(
        reverse("wallet-top-up-webhook-fail", kwargs={"transaction_id": transaction_id}),
        {
            "external_reference": "mp-payment-789",
            "provider_status": "REJECTED",
            "failure_reason": "payment_rejected",
        },
        format="json",
        HTTP_X_WEBHOOK_SECRET=settings.PAYFLOW_WEBHOOK_SECRET,
    )

    wallet.refresh_from_db()
    transaction = WalletTransaction.objects.get(id=transaction_id)

    assert webhook_response.status_code == 200
    assert transaction.status == "FAILED"
    assert transaction.provider_status == "REJECTED"
    assert transaction.failure_reason == "payment_rejected"
    assert wallet.balance == Decimal("0.00")

    reference = f"wallet_transaction_{transaction_id}"
    assert LedgerEntry.objects.filter(reference=reference).count() == 0


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_fail_webhook_creates_failed_audit_log(
    mercado_pago_service_mock,
    authenticated_client,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/fail-audit-123",
        "provider_reference": "pref_fail_audit_123",
    }

    create_response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "33.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    transaction_id = create_response.data["id"]

    webhook_response = authenticated_client.post(
        reverse("wallet-top-up-webhook-fail", kwargs={"transaction_id": transaction_id}),
        {
            "provider_status": "FAILED",
            "failure_reason": "provider_timeout",
        },
        format="json",
        HTTP_X_WEBHOOK_SECRET=settings.PAYFLOW_WEBHOOK_SECRET,
    )

    failed_log = AuditLog.objects.filter(
        action="WALLET_TOP_UP_FAILED",
        entity_type="wallet_transaction",
        entity_id=transaction_id,
    ).first()

    assert webhook_response.status_code == 200
    assert failed_log is not None
    assert failed_log.metadata["failure_reason"] == "provider_timeout"


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_webhook_rejects_invalid_secret(
    mercado_pago_service_mock,
    authenticated_client,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/secret-123",
        "provider_reference": "pref_secret_123",
    }

    create_response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "25.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    transaction_id = create_response.data["id"]

    response = authenticated_client.post(
        reverse("wallet-top-up-webhook-complete", kwargs={"transaction_id": transaction_id}),
        {
            "external_reference": "mp-invalid-secret",
            "provider_status": "APPROVED",
        },
        format="json",
        HTTP_X_WEBHOOK_SECRET="wrong-secret",
    )

    assert response.status_code == 403
    assert response.data["error"] == "Invalid webhook secret"