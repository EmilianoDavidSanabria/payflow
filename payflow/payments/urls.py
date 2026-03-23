from django.urls import path

from payments.views import (
    CreatePaymentView,
    PaymentHistoryView,
    PaymentDetailView,
    RecentRecipientsView,
    FrequentRecipientsView,
)
from payments.request_views import (
    CreatePaymentRequestView,
    PaymentRequestListView,
    PaymentRequestDetailView,
    AcceptPaymentRequestView,
    RejectPaymentRequestView,
)

urlpatterns = [
    path("create/", CreatePaymentView.as_view(), name="create-payment"),
    path("history/", PaymentHistoryView.as_view(), name="payment-history"),
    path(
        "recent-recipients/",
        RecentRecipientsView.as_view(),
        name="recent-recipients",
    ),
    path(
        "frequent-recipients/",
        FrequentRecipientsView.as_view(),
        name="frequent-recipients",
    ),
    path(
        "requests/create/",
        CreatePaymentRequestView.as_view(),
        name="create-payment-request",
    ),
    path(
        "requests/",
        PaymentRequestListView.as_view(),
        name="payment-request-list",
    ),
    path(
        "requests/<int:request_id>/",
        PaymentRequestDetailView.as_view(),
        name="payment-request-detail",
    ),
    path(
        "requests/<int:request_id>/accept/",
        AcceptPaymentRequestView.as_view(),
        name="accept-payment-request",
    ),
    path(
        "requests/<int:request_id>/reject/",
        RejectPaymentRequestView.as_view(),
        name="reject-payment-request",
    ),
    path("<int:payment_id>/", PaymentDetailView.as_view(), name="payment-detail"),
]