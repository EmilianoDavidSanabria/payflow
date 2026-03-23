from decimal import Decimal

import pytest
from django.urls import reverse

from payments.models import PaymentRequest
from .helpers import authenticate_client, create_user


@pytest.mark.django_db
def test_payment_request_list_includes_incoming_and_outgoing():
    requester = create_user("request_list_requester")
    requested_from = create_user("request_list_payer")
    third_user = create_user("request_list_third")

    outgoing_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("15.00"),
    )

    incoming_request = PaymentRequest.objects.create(
        requester=third_user,
        requested_from=requester,
        amount=Decimal("20.00"),
    )

    client = authenticate_client(requester)

    response = client.get(reverse("payment-request-list"))

    assert response.status_code == 200
    assert response.data["count"] == 2

    returned_ids = {item["id"] for item in response.data["results"]}
    assert returned_ids == {outgoing_request.id, incoming_request.id}


@pytest.mark.django_db
def test_payment_request_list_filters_by_incoming_type():
    user = create_user("request_incoming_user")
    other = create_user("request_incoming_other")
    third = create_user("request_incoming_third")

    incoming_request = PaymentRequest.objects.create(
        requester=other,
        requested_from=user,
        amount=Decimal("10.00"),
    )

    PaymentRequest.objects.create(
        requester=user,
        requested_from=third,
        amount=Decimal("20.00"),
    )

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-request-list"),
        {"type": "incoming"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["type"] == "incoming"
    assert response.data["results"][0]["id"] == incoming_request.id
    assert response.data["results"][0]["direction"] == "incoming"


@pytest.mark.django_db
def test_payment_request_list_filters_by_status():
    user = create_user("request_status_user")
    other = create_user("request_status_other")

    pending_request = PaymentRequest.objects.create(
        requester=user,
        requested_from=other,
        amount=Decimal("11.00"),
        status="PENDING",
    )

    PaymentRequest.objects.create(
        requester=user,
        requested_from=other,
        amount=Decimal("22.00"),
        status="REJECTED",
    )

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-request-list"),
        {"status": "PENDING"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["status"] == "PENDING"
    assert response.data["results"][0]["id"] == pending_request.id


@pytest.mark.django_db
def test_payment_request_list_filters_by_username():
    user = create_user("request_username_user")
    bob = create_user("request_username_bob")
    charlie = create_user("request_username_charlie")

    matching_request = PaymentRequest.objects.create(
        requester=user,
        requested_from=bob,
        amount=Decimal("15.00"),
    )

    PaymentRequest.objects.create(
        requester=charlie,
        requested_from=user,
        amount=Decimal("30.00"),
    )

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-request-list"),
        {"username": "request_username_bob"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["username"] == "request_username_bob"
    assert response.data["results"][0]["id"] == matching_request.id


@pytest.mark.django_db
def test_payment_request_list_filters_by_date_from():
    user = create_user("request_date_user")
    other = create_user("request_date_other")

    payment_request = PaymentRequest.objects.create(
        requester=user,
        requested_from=other,
        amount=Decimal("18.00"),
    )

    client = authenticate_client(user)

    today = payment_request.created_at.date().isoformat()

    response = client.get(
        reverse("payment-request-list"),
        {"date_from": today},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["date_from"] == today


@pytest.mark.django_db
def test_payment_request_list_rejects_invalid_type():
    user = create_user("request_invalid_type_user")

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-request-list"),
        {"type": "weird"},
    )

    assert response.status_code == 400
    assert "type must be one of" in response.data["error"]


@pytest.mark.django_db
def test_payment_request_list_rejects_invalid_status():
    user = create_user("request_invalid_status_user")

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-request-list"),
        {"status": "BROKEN"},
    )

    assert response.status_code == 400
    assert "status must be one of" in response.data["error"]


@pytest.mark.django_db
def test_payment_request_list_rejects_invalid_date_from():
    user = create_user("request_invalid_date_user")

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-request-list"),
        {"date_from": "not-a-date"},
    )

    assert response.status_code == 400
    assert "date_from must be in YYYY-MM-DD format" in response.data["error"]


@pytest.mark.django_db
def test_payment_request_list_contract_includes_expected_top_level_keys():
    user = create_user("request_contract_user")
    other = create_user("request_contract_other")

    PaymentRequest.objects.create(
        requester=user,
        requested_from=other,
        amount=Decimal("14.00"),
    )

    client = authenticate_client(user)

    response = client.get(reverse("payment-request-list"))

    assert response.status_code == 200
    assert set(response.data.keys()) == {
        "count",
        "page",
        "page_size",
        "total_pages",
        "type",
        "status",
        "username",
        "date_from",
        "date_to",
        "results",
    }


@pytest.mark.django_db
def test_payment_request_list_contract_result_item_has_expected_keys():
    user = create_user("request_item_user")
    other = create_user("request_item_other")

    PaymentRequest.objects.create(
        requester=user,
        requested_from=other,
        amount=Decimal("19.00"),
    )

    client = authenticate_client(user)

    response = client.get(reverse("payment-request-list"))

    assert response.status_code == 200
    assert len(response.data["results"]) == 1

    item = response.data["results"][0]

    assert set(item.keys()) == {
        "id",
        "requester",
        "requester_username",
        "requested_from",
        "requested_from_username",
        "amount",
        "status",
        "accepted_payment_id",
        "created_at",
        "updated_at",
        "resolved_at",
        "direction",
        "counterparty_username",
    }