import pytest
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from wallets.models import WalletTransaction


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_intent_creates_checkout_url_for_mercado_pago(
    mercado_pago_service_mock,
    authenticated_client,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/real-flow-123",
        "provider_reference": "pref_real_123",
    }

    response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "120.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == "PENDING"
    assert response.data["rail"] == "MERCADO_PAGO"
    assert response.data["checkout_url"] == "https://mp.test/checkout/real-flow-123"
    assert response.data["provider_status"] == "CHECKOUT_CREATED"


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_intent_sets_external_reference_before_creating_preference(
    mercado_pago_service_mock,
    authenticated_client,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.return_value = {
        "checkout_url": "https://mp.test/checkout/ref-123",
        "provider_reference": "pref_ref_123",
    }

    response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "80.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    assert response.status_code == 201

    call_args = mercado_pago_service_instance.create_top_up_preference.call_args[0]
    wallet_transaction = call_args[0]

    assert wallet_transaction.external_reference == str(wallet_transaction.id)
    assert response.data["external_reference"] == str(response.data["id"])


@pytest.mark.django_db
@patch("wallets.provider_funding_views.MercadoPagoService")
def test_wallet_top_up_intent_marks_transaction_as_failed_when_preference_creation_fails(
    mercado_pago_service_mock,
    authenticated_client,
):
    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.create_top_up_preference.side_effect = Exception(
        "mercado pago unavailable"
    )

    response = authenticated_client.post(
        reverse("wallet-top-up-intent"),
        {
            "amount": "42.00",
            "rail": "MERCADO_PAGO",
        },
        format="json",
    )

    assert response.status_code == 502
    assert (
        response.data["detail"]
        == "Could not create Mercado Pago checkout: mercado pago unavailable"
    )

    transaction = WalletTransaction.objects.get()

    assert transaction.transaction_type == "TOP_UP"
    assert transaction.amount == Decimal("42.00")
    assert transaction.rail == "MERCADO_PAGO"
    assert transaction.status == "FAILED"
    assert transaction.provider_status == "PREFERENCE_CREATION_FAILED"
    assert transaction.failure_reason == "mercado pago unavailable"
    assert transaction.external_reference == str(transaction.id)
    assert transaction.checkout_url in (None, "")


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_completes_pending_top_up_from_real_payment_status(
    mercado_pago_service_mock,
    authenticated_client,
    wallet,
):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("150.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="temp",
        provider_status="CHECKOUT_CREATED",
    )

    transaction.external_reference = str(transaction.id)
    transaction.save(update_fields=["external_reference", "updated_at"])

    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.get_payment.return_value = {
        "id": 999001,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": str(transaction.id),
    }

    response = authenticated_client.post(
        reverse("mercadopago-webhook"),
        {
            "data": {
                "id": "999001",
            }
        },
        format="json",
    )

    transaction.refresh_from_db()
    wallet.refresh_from_db()

    assert response.status_code == 200
    assert transaction.status == "COMPLETED"
    assert transaction.provider_status == "approved"
    assert wallet.balance == Decimal("150.00")


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_fails_pending_top_up_when_payment_is_rejected(
    mercado_pago_service_mock,
    authenticated_client,
    wallet,
):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("95.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="temp",
        provider_status="CHECKOUT_CREATED",
    )

    transaction.external_reference = str(transaction.id)
    transaction.save(update_fields=["external_reference", "updated_at"])

    mercado_pago_service_instance = mercado_pago_service_mock.return_value
    mercado_pago_service_instance.get_payment.return_value = {
        "id": 999002,
        "status": "rejected",
        "status_detail": "cc_rejected_other_reason",
        "external_reference": str(transaction.id),
    }

    response = authenticated_client.post(
        reverse("mercadopago-webhook"),
        {
            "data": {
                "id": "999002",
            }
        },
        format="json",
    )

    transaction.refresh_from_db()
    wallet.refresh_from_db()

    assert response.status_code == 200
    assert transaction.status == "FAILED"
    assert transaction.provider_status == "rejected"
    assert transaction.failure_reason == "cc_rejected_other_reason"
    assert wallet.balance == Decimal("0.00")