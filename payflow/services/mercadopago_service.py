import mercadopago
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class MercadoPagoService:
    def __init__(self):
        access_token = settings.MERCADO_PAGO_ACCESS_TOKEN

        if not access_token:
            raise ImproperlyConfigured("MERCADO_PAGO_ACCESS_TOKEN is not configured")

        self.sdk = mercadopago.SDK(access_token)

    def create_top_up_preference(self, wallet_transaction):
        if wallet_transaction.wallet.currency != "ARS":
            raise ValueError(
                "Mercado Pago top-ups are currently supported only in ARS wallets"
            )

        preference_data = {
            "items": [
                {
                    "title": "PayFlow Wallet Top Up",
                    "quantity": 1,
                    "currency_id": wallet_transaction.wallet.currency,
                    "unit_price": float(wallet_transaction.amount),
                }
            ],
            "external_reference": wallet_transaction.external_reference,
        }

        if settings.MERCADO_PAGO_WEBHOOK_URL:
            preference_data["notification_url"] = settings.MERCADO_PAGO_WEBHOOK_URL

        frontend_base_url = getattr(settings, "PAYFLOW_FRONTEND_URL", "").rstrip("/")

        can_use_back_urls = (
            frontend_base_url
            and not frontend_base_url.startswith("http://localhost")
            and not frontend_base_url.startswith("http://127.0.0.1")
            and not frontend_base_url.startswith("https://localhost")
            and not frontend_base_url.startswith("https://127.0.0.1")
        )

        if can_use_back_urls:
            preference_data["back_urls"] = {
                "success": f"{frontend_base_url}/wallet?topup=success",
                "failure": f"{frontend_base_url}/wallet?topup=failure",
                "pending": f"{frontend_base_url}/wallet?topup=pending",
            }
            preference_data["auto_return"] = "approved"

        result = self.sdk.preference().create(preference_data)

        status_code = result.get("status")
        response = result.get("response", {}) or {}

        if status_code and status_code >= 400:
            raise ValueError(
                f"Mercado Pago preference error | status={status_code} | response={response}"
            )

        checkout_url = response.get("init_point")

        if not checkout_url:
            sandbox_url = response.get("sandbox_init_point")
            if sandbox_url:
                raise ValueError(
                    "Mercado Pago returned a sandbox checkout URL. Real top-ups require a production init_point."
                )

            raise ValueError(
                f"Mercado Pago preference missing checkout URL | status={status_code} | response={response}"
            )

        return {
            "checkout_url": checkout_url,
            "provider_reference": response.get("id"),
        }

    def get_payment(self, payment_id):
        result = self.sdk.payment().get(payment_id)
        return result.get("response", {}) or {}

    def search_payment_by_external_reference(self, external_reference):
        result = self.sdk.payment().search(
            {
                "external_reference": str(external_reference),
                "sort": "date_created",
                "criteria": "desc",
                "limit": 1,
            }
        )

        response = result.get("response", {}) or {}
        results = response.get("results", []) or []

        if not results:
            return {}

        return results[0]