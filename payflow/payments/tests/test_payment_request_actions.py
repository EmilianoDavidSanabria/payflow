from decimal import Decimal

import pytest
from django.urls import reverse

from payments.models import Payment, PaymentRequest

from .helpers import authenticate_client, create_user


@pytest.mark.django_db
def test_create_payment_request_success():
    requester = create_user("requester_user", balance="10.00")
    requested_from = create_user("payer_user", balance="100.00")

    client = authenticate_client(requester)

    response = client.post(
        reverse("create-payment-request"),
        {
            "requested_from_username": requested_from.username,
            "amount": "25.00",
        },
        format="json",
    )

    assert response.status_code == 201
    assert PaymentRequest.objects.count() == 1

    payment_request = PaymentRequest.objects.get()
    assert payment_request.requester == requester
    assert payment_request.requested_from == requested_from
    assert payment_request.amount == Decimal("25.00")
    assert payment_request.status == "PENDING"


@pytest.mark.django_db
def test_payment_request_rejects_self_request():
    user = create_user("self_request_user")

    client = authenticate_client(user)

    response = client.post(
        reverse("create-payment-request"),
        {
            "requested_from_username": user.username,
            "amount": "10.00",
        },
        format="json",
    )

    assert response.status_code == 400
    assert PaymentRequest.objects.count() == 0


@pytest.mark.django_db
def test_accept_payment_request_creates_payment_and_marks_request_accepted():
    requester = create_user("accept_requester", balance="5.00")
    requested_from = create_user("accept_payer", balance="100.00")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("30.00"),
    )

    client = authenticate_client(requested_from)

    response = client.post(
        reverse("accept-payment-request", kwargs={"request_id": payment_request.id}),
        format="json",
    )

    requester.wallet.refresh_from_db()
    requested_from.wallet.refresh_from_db()
    payment_request.refresh_from_db()

    assert response.status_code == 200
    assert payment_request.status == "ACCEPTED"
    assert payment_request.accepted_payment is not None
    assert Payment.objects.count() == 1

    payment = Payment.objects.get()
    assert payment.sender == requested_from
    assert payment.receiver == requester
    assert payment.amount == Decimal("30.00")
    assert payment.status == "COMPLETED"

    assert requested_from.wallet.balance == Decimal("70.00")
    assert requester.wallet.balance == Decimal("35.00")


@pytest.mark.django_db
def test_reject_payment_request_marks_request_rejected():
    requester = create_user("reject_requester")
    requested_from = create_user("reject_payer")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("18.00"),
    )

    client = authenticate_client(requested_from)

    response = client.post(
        reverse("reject-payment-request", kwargs={"request_id": payment_request.id}),
        format="json",
    )

    payment_request.refresh_from_db()

    assert response.status_code == 200
    assert payment_request.status == "REJECTED"
    assert payment_request.accepted_payment is None
    assert Payment.objects.count() == 0


@pytest.mark.django_db
def test_only_requested_user_can_accept_payment_request():
    requester = create_user("perm_requester")
    requested_from = create_user("perm_payer")
    stranger = create_user("perm_stranger")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("22.00"),
    )

    client = authenticate_client(stranger)

    response = client.post(
        reverse("accept-payment-request", kwargs={"request_id": payment_request.id}),
        format="json",
    )

    payment_request.refresh_from_db()

    assert response.status_code == 403
    assert payment_request.status == "PENDING"
    assert Payment.objects.count() == 0


@pytest.mark.django_db
def test_accept_payment_request_with_insufficient_balance_keeps_request_pending():
    requester = create_user("low_balance_requester", balance="0.00")
    requested_from = create_user("low_balance_payer", balance="5.00")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("20.00"),
    )

    client = authenticate_client(requested_from)

    response = client.post(
        reverse("accept-payment-request", kwargs={"request_id": payment_request.id}),
        format="json",
    )

    payment_request.refresh_from_db()
    requester.wallet.refresh_from_db()
    requested_from.wallet.refresh_from_db()

    assert response.status_code == 400
    assert response.data["error"] == "Insufficient balance"
    assert payment_request.status == "PENDING"
    assert payment_request.accepted_payment is None
    assert Payment.objects.count() == 0
    assert requester.wallet.balance == Decimal("0.00")
    assert requested_from.wallet.balance == Decimal("5.00")