from django.urls import path

from .views import WalletView
from .funding_views import (
    WalletTopUpView,
    WalletWithdrawalView,
    WalletTransactionListView,
    WalletTransactionDetailView,
    WalletTransactionRefreshStatusView,
)
from .provider_funding_views import WalletTopUpIntentView

urlpatterns = [
    path("me/", WalletView.as_view(), name="wallet-me"),
    path("me/top-up/", WalletTopUpView.as_view(), name="wallet-top-up"),
    path("me/top-up-intents/", WalletTopUpIntentView.as_view(), name="wallet-top-up-intent"),
    path("me/withdraw/", WalletWithdrawalView.as_view(), name="wallet-withdraw"),
    path("me/transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
    path(
        "me/transactions/<int:transaction_id>/",
        WalletTransactionDetailView.as_view(),
        name="wallet-transaction-detail",
    ),
    path(
        "me/transactions/<int:transaction_id>/refresh-status/",
        WalletTransactionRefreshStatusView.as_view(),
        name="wallet-transaction-refresh-status",
    ),
]