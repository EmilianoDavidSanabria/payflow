import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

from services.mercadopago_service import MercadoPagoService
from wallets.models import Wallet, WalletTransaction


def create_wallet_transaction(amount=Decimal("100.00"), currency="ARS", external_reference="123"):
    User = get_user_model()
    user = User.objects.create_user(
        username=f"user_{external_reference}",
        password="testpass123",
    )
    wallet = Wallet.objects.get(user=user)
    wallet.currency = currency
    wallet.save(update_fields=["currency", "updated_at"])

    return WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=amount,
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference=external_reference,
        provider_status="CREATED",
    )


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_init_raises_when_access_token_is_missing(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = ""

    with pytest.raises(
        ImproperlyConfigured,
        match="MERCADO_PAGO_ACCESS_TOKEN is not configured",
    ):
        MercadoPagoService()

    sdk_mock.assert_not_called()


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_init_creates_sdk_with_access_token(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = "test-token-123"

    service = MercadoPagoService()

    sdk_mock.assert_called_once_with("test-token-123")
    assert service.sdk == sdk_mock.return_value


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_create_top_up_preference_uses_localhost_without_back_urls(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = "test-token"
    settings.MERCADO_PAGO_WEBHOOK_URL = "https://api.test/webhooks/mercadopago/"
    settings.PAYFLOW_FRONTEND_URL = "http://localhost:5173"

    wallet_transaction = create_wallet_transaction(
        amount=Decimal("120.50"),
        currency="ARS",
        external_reference="tx-local-1",
    )

    sdk_instance = sdk_mock.return_value
    preference_resource = Mock()
    sdk_instance.preference.return_value = preference_resource
    preference_resource.create.return_value = {
        "status": 201,
        "response": {
            "id": "pref_local_123",
            "init_point": "https://mp.test/checkout/local-123",
        },
    }

    service = MercadoPagoService()
    result = service.create_top_up_preference(wallet_transaction)

    preference_resource.create.assert_called_once()
    payload = preference_resource.create.call_args[0][0]

    assert payload["items"] == [
        {
            "title": "PayFlow Wallet Top Up",
            "quantity": 1,
            "currency_id": "ARS",
            "unit_price": 120.5,
        }
    ]
    assert payload["external_reference"] == "tx-local-1"
    assert payload["notification_url"] == "https://api.test/webhooks/mercadopago/"
    assert "back_urls" not in payload
    assert "auto_return" not in payload

    assert result == {
        "checkout_url": "https://mp.test/checkout/local-123",
        "provider_reference": "pref_local_123",
    }


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_create_top_up_preference_includes_back_urls_for_public_frontend(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = "test-token"
    settings.MERCADO_PAGO_WEBHOOK_URL = "https://api.test/webhooks/mercadopago/"
    settings.PAYFLOW_FRONTEND_URL = "https://payflow-frontend.app"

    wallet_transaction = create_wallet_transaction(
        amount=Decimal("80.00"),
        currency="ARS",
        external_reference="tx-public-1",
    )

    sdk_instance = sdk_mock.return_value
    preference_resource = Mock()
    sdk_instance.preference.return_value = preference_resource
    preference_resource.create.return_value = {
        "status": 201,
        "response": {
            "id": "pref_public_123",
            "sandbox_init_point": "https://sandbox.mercadopago.com/checkout/public-123",
        },
    }

    service = MercadoPagoService()
    result = service.create_top_up_preference(wallet_transaction)

    preference_resource.create.assert_called_once()
    payload = preference_resource.create.call_args[0][0]

    assert payload["external_reference"] == "tx-public-1"
    assert payload["notification_url"] == "https://api.test/webhooks/mercadopago/"
    assert payload["back_urls"] == {
        "success": "https://payflow-frontend.app/wallet?topup=success",
        "failure": "https://payflow-frontend.app/wallet?topup=failure",
        "pending": "https://payflow-frontend.app/wallet?topup=pending",
    }
    assert payload["auto_return"] == "approved"

    assert result == {
        "checkout_url": "https://sandbox.mercadopago.com/checkout/public-123",
        "provider_reference": "pref_public_123",
    }


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_create_top_up_preference_raises_when_provider_returns_error_status(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = "test-token"
    settings.MERCADO_PAGO_WEBHOOK_URL = "https://api.test/webhooks/mercadopago/"
    settings.PAYFLOW_FRONTEND_URL = "https://payflow-frontend.app"

    wallet_transaction = create_wallet_transaction(external_reference="tx-error-1")

    sdk_instance = sdk_mock.return_value
    preference_resource = Mock()
    sdk_instance.preference.return_value = preference_resource
    preference_resource.create.return_value = {
        "status": 400,
        "response": {
            "message": "invalid_auto_return",
            "error": "bad_request",
        },
    }

    service = MercadoPagoService()

    with pytest.raises(
        ValueError,
        match=r"Mercado Pago preference error \| status=400 \| response=",
    ):
        service.create_top_up_preference(wallet_transaction)


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_create_top_up_preference_raises_when_checkout_url_is_missing(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = "test-token"
    settings.MERCADO_PAGO_WEBHOOK_URL = "https://api.test/webhooks/mercadopago/"
    settings.PAYFLOW_FRONTEND_URL = "https://payflow-frontend.app"

    wallet_transaction = create_wallet_transaction(external_reference="tx-no-url-1")

    sdk_instance = sdk_mock.return_value
    preference_resource = Mock()
    sdk_instance.preference.return_value = preference_resource
    preference_resource.create.return_value = {
        "status": 201,
        "response": {
            "id": "pref_no_url_123",
        },
    }

    service = MercadoPagoService()

    with pytest.raises(
        ValueError,
        match=r"Mercado Pago preference missing checkout URL \| status=201 \| response=",
    ):
        service.create_top_up_preference(wallet_transaction)


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_get_payment_returns_provider_response_or_empty_dict(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = "test-token"

    sdk_instance = sdk_mock.return_value
    payment_resource = Mock()
    sdk_instance.payment.return_value = payment_resource
    payment_resource.get.side_effect = [
        {
            "response": {
                "id": 999001,
                "status": "approved",
                "external_reference": "55",
            }
        },
        {
            "response": None,
        },
    ]

    service = MercadoPagoService()

    first_result = service.get_payment("999001")
    second_result = service.get_payment("999002")

    assert first_result == {
        "id": 999001,
        "status": "approved",
        "external_reference": "55",
    }
    assert second_result == {}


@pytest.mark.django_db
@patch("services.mercadopago_service.mercadopago.SDK")
def test_search_payment_by_external_reference_returns_latest_result_or_empty_dict(sdk_mock, settings):
    settings.MERCADO_PAGO_ACCESS_TOKEN = "test-token"

    sdk_instance = sdk_mock.return_value
    payment_resource = Mock()
    sdk_instance.payment.return_value = payment_resource
    payment_resource.search.side_effect = [
        {
            "response": {
                "results": [
                    {
                        "id": 888001,
                        "status": "approved",
                        "external_reference": "77",
                    }
                ]
            }
        },
        {
            "response": {
                "results": [],
            }
        },
    ]

    service = MercadoPagoService()

    found_result = service.search_payment_by_external_reference(77)
    empty_result = service.search_payment_by_external_reference("missing-ref")

    first_payload = payment_resource.search.call_args_list[0][0][0]
    second_payload = payment_resource.search.call_args_list[1][0][0]

    assert first_payload == {
        "external_reference": "77",
        "sort": "date_created",
        "criteria": "desc",
        "limit": 1,
    }
    assert second_payload == {
        "external_reference": "missing-ref",
        "sort": "date_created",
        "criteria": "desc",
        "limit": 1,
    }

    assert found_result == {
        "id": 888001,
        "status": "approved",
        "external_reference": "77",
    }
    assert empty_result == {}