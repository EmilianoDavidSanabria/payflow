from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from wallets.models import Wallet, WalletTransaction


def create_mercadopago_top_up_transaction(
    *,
    amount=Decimal("100.00"),
    status="PENDING",
    provider_status="CHECKOUT_CREATED",
    external_reference=None,
):
    User = get_user_model()
    user = User.objects.create_user(
        username=f"mp_webhook_user_{WalletTransaction.objects.count() + 1}",
        password="testpass123",
    )
    wallet = Wallet.objects.get(user=user)
    wallet.currency = "ARS"
    wallet.save(update_fields=["currency", "updated_at"])

    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=amount,
        status=status,
        rail="MERCADO_PAGO",
        external_reference="temp",
        provider_status=provider_status,
    )

    transaction.external_reference = external_reference or str(transaction.id)
    transaction.save(update_fields=["external_reference", "updated_at"])

    return transaction


@pytest.mark.django_db
def test_mercadopago_webhook_ignores_request_when_payment_id_is_missing():
    client = APIClient()

    response = client.post(
        reverse("mercadopago-webhook"),
        {},
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {"status": "ignored"}


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed")
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_returns_already_processed_when_event_was_seen_before(
    mercado_pago_service_mock,
    already_processed_mock,
):
    client = APIClient()
    already_processed_mock.return_value = True

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_123",
            "data": {"id": "999001"},
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {"status": "already_processed"}
    already_processed_mock.assert_called_once_with("mercadopago", "mp_event:evt_123")
    mercado_pago_service_mock.assert_not_called()


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_returns_502_when_payment_fetch_raises_error(
    mercado_pago_service_mock,
    _already_processed_mock,
):
    client = APIClient()
    mercado_pago_service_mock.return_value.get_payment.side_effect = Exception("mp unavailable")

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_124",
            "data": {"id": "999002"},
        },
        format="json",
    )

    assert response.status_code == 502
    assert response.data == {
        "detail": "Could not fetch payment from Mercado Pago: mp unavailable"
    }


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_returns_502_when_payment_response_is_empty(
    mercado_pago_service_mock,
    _already_processed_mock,
):
    client = APIClient()
    mercado_pago_service_mock.return_value.get_payment.return_value = {}

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_125",
            "data": {"id": "999003"},
        },
        format="json",
    )

    assert response.status_code == 502
    assert response.data == {"detail": "Could not fetch payment from Mercado Pago"}


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_returns_400_when_payment_has_no_external_reference(
    mercado_pago_service_mock,
    _already_processed_mock,
):
    client = APIClient()
    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999004,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": None,
    }

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_126",
            "data": {"id": "999004"},
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data == {"detail": "Missing external reference"}


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_returns_404_when_wallet_transaction_does_not_exist(
    mercado_pago_service_mock,
    _already_processed_mock,
):
    client = APIClient()
    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999005,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": "999999",
    }

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_127",
            "data": {"id": "999005"},
        },
        format="json",
    )

    assert response.status_code == 404
    assert response.data == {"detail": "Wallet transaction not found"}


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_returns_existing_transaction_when_already_terminal(
    mercado_pago_service_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    client = APIClient()
    transaction = create_mercadopago_top_up_transaction(
        status="COMPLETED",
        provider_status="approved",
    )

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999006,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": str(transaction.id),
    }

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_128",
            "data": {"id": "999006"},
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["id"] == transaction.id
    assert response.data["status"] == "COMPLETED"
    assert response.data["provider_status"] == "approved"

    mark_processed_mock.assert_called_once_with("mercadopago", "mp_event:evt_128")


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_updates_provider_status_for_non_terminal_payment(
    mercado_pago_service_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    client = APIClient()
    transaction = create_mercadopago_top_up_transaction(
        status="PENDING",
        provider_status="CHECKOUT_CREATED",
    )

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999007,
        "status": "in_process",
        "status_detail": "pending_contingency",
        "external_reference": str(transaction.id),
    }

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_129",
            "data": {"id": "999007"},
        },
        format="json",
    )

    transaction.refresh_from_db()

    assert response.status_code == 200
    assert response.data["id"] == transaction.id
    assert response.data["status"] == "PENDING"
    assert response.data["provider_status"] == "in_process"
    assert transaction.status == "PENDING"
    assert transaction.provider_status == "in_process"

    mark_processed_mock.assert_called_once_with("mercadopago", "mp_event:evt_129")


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.WalletFundingService.complete_top_up")
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_completes_top_up_when_status_is_approved(
    mercado_pago_service_mock,
    complete_top_up_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    client = APIClient()
    transaction = create_mercadopago_top_up_transaction(
        amount=Decimal("150.00"),
        status="PENDING",
        provider_status="CHECKOUT_CREATED",
    )

    completed_transaction = transaction
    completed_transaction.status = "COMPLETED"
    completed_transaction.provider_status = "approved"

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999008,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": str(transaction.id),
    }
    complete_top_up_mock.return_value = completed_transaction

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_130",
            "data": {"id": "999008"},
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["id"] == transaction.id
    assert response.data["status"] == "COMPLETED"
    assert response.data["provider_status"] == "approved"

    complete_top_up_mock.assert_called_once_with(
        wallet_transaction_id=transaction.id,
        external_reference=str(transaction.id),
        provider_status="approved",
        provider_payment_id="999008",
        provider_amount=None,
        provider_currency=None,
    )
    mark_processed_mock.assert_called_once_with("mercadopago", "mp_event:evt_130")


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.WalletFundingService.fail_top_up")
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_fails_top_up_when_status_is_terminal_failure(
    mercado_pago_service_mock,
    fail_top_up_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    client = APIClient()
    transaction = create_mercadopago_top_up_transaction(
        amount=Decimal("95.00"),
        status="PENDING",
        provider_status="CHECKOUT_CREATED",
    )

    failed_transaction = transaction
    failed_transaction.status = "FAILED"
    failed_transaction.provider_status = "rejected"
    failed_transaction.failure_reason = "cc_rejected_other_reason"

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999009,
        "status": "rejected",
        "status_detail": "cc_rejected_other_reason",
        "external_reference": str(transaction.id),
    }
    fail_top_up_mock.return_value = failed_transaction

    response = client.post(
        reverse("mercadopago-webhook"),
        {
            "id": "evt_131",
            "data": {"id": "999009"},
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["id"] == transaction.id
    assert response.data["status"] == "FAILED"
    assert response.data["provider_status"] == "rejected"
    assert response.data["failure_reason"] == "cc_rejected_other_reason"

    fail_top_up_mock.assert_called_once_with(
        wallet_transaction_id=transaction.id,
        provider_status="rejected",
        failure_reason="cc_rejected_other_reason",
        external_reference=str(transaction.id),
    )
    mark_processed_mock.assert_called_once_with("mercadopago", "mp_event:evt_131")


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_extracts_payment_id_from_query_params(
    mercado_pago_service_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    client = APIClient()
    transaction = create_mercadopago_top_up_transaction(
        status="COMPLETED",
        provider_status="approved",
    )

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999010,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": str(transaction.id),
    }

    response = client.post(
        f"{reverse('mercadopago-webhook')}?data.id=999010&topic=payment&action=updated",
        {},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["id"] == transaction.id

    mark_processed_mock.assert_called_once()


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_does_not_credit_when_amount_mismatches(
    mercado_pago_service_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    """Fase 5: monto incorrecto -> no se acredita, queda PENDING."""
    client = APIClient()
    transaction = create_mercadopago_top_up_transaction(
        amount=Decimal("100.00"),
        status="PENDING",
        provider_status="CHECKOUT_CREATED",
    )

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999011,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": str(transaction.id),
        "transaction_amount": 1.00,  # distinto de los 100.00 esperados
        "currency_id": "ARS",
    }

    response = client.post(
        reverse("mercadopago-webhook"),
        {"id": "evt_132", "data": {"id": "999011"}},
        format="json",
    )

    transaction.refresh_from_db()

    assert response.status_code == 409
    assert transaction.status == "PENDING"
    assert transaction.provider_payment_id is None
    mark_processed_mock.assert_called_once_with("mercadopago", "mp_event:evt_132")


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_does_not_credit_when_currency_mismatches(
    mercado_pago_service_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    """Fase 5: moneda incorrecta -> no se acredita, queda PENDING."""
    client = APIClient()
    transaction = create_mercadopago_top_up_transaction(
        amount=Decimal("100.00"),
        status="PENDING",
        provider_status="CHECKOUT_CREATED",
    )

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999012,
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": str(transaction.id),
        "transaction_amount": 100.00,
        "currency_id": "USD",  # la wallet de create_mercadopago_top_up_transaction es ARS
    }

    response = client.post(
        reverse("mercadopago-webhook"),
        {"id": "evt_133", "data": {"id": "999012"}},
        format="json",
    )

    transaction.refresh_from_db()

    assert response.status_code == 409
    assert transaction.status == "PENDING"


@pytest.mark.django_db
@patch("webhook.mercadopago_webhook_views.mark_webhook_event_processed")
@patch("webhook.mercadopago_webhook_views.webhook_event_already_processed", return_value=False)
@patch("webhook.mercadopago_webhook_views.MercadoPagoService")
def test_mercadopago_webhook_does_not_credit_when_payment_id_already_used_elsewhere(
    mercado_pago_service_mock,
    _already_processed_mock,
    mark_processed_mock,
):
    """
    Fase 5: 'payment ID ya utilizado en otra transacción'. Simula que el
    mismo payment_id de MP ya se usó para completar OTRA WalletTransaction,
    y verifica que un segundo webhook con ese mismo payment_id, apuntando
    a una transacción distinta, no acredite nada.
    """
    client = APIClient()

    already_credited = create_mercadopago_top_up_transaction(
        amount=Decimal("30.00"),
        status="COMPLETED",
        provider_status="approved",
    )
    already_credited.provider_payment_id = "999013"
    already_credited.save(update_fields=["provider_payment_id", "updated_at"])

    other_transaction = create_mercadopago_top_up_transaction(
        amount=Decimal("30.00"),
        status="PENDING",
        provider_status="CHECKOUT_CREATED",
    )

    mercado_pago_service_mock.return_value.get_payment.return_value = {
        "id": 999013,  # mismo payment_id que already_credited
        "status": "approved",
        "status_detail": "accredited",
        "external_reference": str(other_transaction.id),
        "transaction_amount": 30.00,
        "currency_id": "ARS",
    }

    response = client.post(
        reverse("mercadopago-webhook"),
        {"id": "evt_134", "data": {"id": "999013"}},
        format="json",
    )

    other_transaction.refresh_from_db()

    assert response.status_code == 409
    assert other_transaction.status == "PENDING"