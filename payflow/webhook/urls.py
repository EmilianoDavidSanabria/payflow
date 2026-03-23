from django.urls import path

from webhook.views import (
    WalletTopUpCompleteWebhookView,
    WalletTopUpFailWebhookView,
)
from webhook.mercadopago_webhook_views import MercadoPagoWebhookView

urlpatterns = [
    path(
        "wallet-top-ups/<int:transaction_id>/complete/",
        WalletTopUpCompleteWebhookView.as_view(),
        name="wallet-top-up-webhook-complete",
    ),
    path(
        "wallet-top-ups/<int:transaction_id>/fail/",
        WalletTopUpFailWebhookView.as_view(),
        name="wallet-top-up-webhook-fail",
    ),
    path(
        "mercadopago/",
        MercadoPagoWebhookView.as_view(),
        name="mercadopago-webhook",
    ),
]