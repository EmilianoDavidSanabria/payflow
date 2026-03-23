from decimal import Decimal

import pytest
from django.urls import reverse

from payments.models import Payment

from .helpers import authenticate_client, create_user


@pytest.mark.django_db
def test_payment_history_includes_sent_and_received_payments():
    sender = create_user("alice_history", balance="100.00")
    receiver = create_user("bob_history", balance="100.00")
    third_user = create_user("charlie_history", balance="100.00")

    p1 = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-1",
    )
    p2 = Payment.objects.create(
        sender=third_user,
        receiver=sender,
        amount=Decimal("15.00"),
        status="COMPLETED",
        idempotency_key="history-2",
    )

    client = authenticate_client(sender)

    url = reverse("payment-history")
    response = client.get(url)

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["page"] == 1
    assert response.data["page_size"] == 10
    assert response.data["total_pages"] == 1
    assert len(response.data["results"]) == 2

    returned_ids = {item["id"] for item in response.data["results"]}
    assert returned_ids == {p1.id, p2.id}


@pytest.mark.django_db
def test_payment_history_filters_by_sent_type():
    sender = create_user("history_sent_sender", balance="100.00")
    receiver = create_user("history_sent_receiver", balance="100.00")
    third_user = create_user("history_sent_third", balance="100.00")

    sent_payment = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-sent-1",
    )
    Payment.objects.create(
        sender=third_user,
        receiver=sender,
        amount=Decimal("15.00"),
        status="COMPLETED",
        idempotency_key="history-sent-2",
    )

    client = authenticate_client(sender)

    response = client.get(reverse("payment-history"), {"type": "sent"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == sent_payment.id
    assert response.data["results"][0]["direction"] == "sent"


@pytest.mark.django_db
def test_payment_history_filters_by_received_type():
    sender = create_user("history_recv_sender", balance="100.00")
    receiver = create_user("history_recv_receiver", balance="100.00")
    third_user = create_user("history_recv_third", balance="100.00")

    Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-recv-1",
    )
    received_payment = Payment.objects.create(
        sender=third_user,
        receiver=sender,
        amount=Decimal("15.00"),
        status="COMPLETED",
        idempotency_key="history-recv-2",
    )

    client = authenticate_client(sender)

    response = client.get(reverse("payment-history"), {"type": "received"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == received_payment.id
    assert response.data["results"][0]["direction"] == "received"


@pytest.mark.django_db
def test_payment_history_filters_by_status():
    sender = create_user("history_status_sender", balance="100.00")
    receiver = create_user("history_status_receiver", balance="100.00")

    completed_payment = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-status-1",
    )
    Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("12.00"),
        status="FAILED",
        idempotency_key="history-status-2",
    )

    client = authenticate_client(sender)

    response = client.get(reverse("payment-history"), {"status": "COMPLETED"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == completed_payment.id
    assert response.data["results"][0]["status"] == "COMPLETED"


@pytest.mark.django_db
def test_payment_history_combines_type_and_status_filters():
    sender = create_user("history_combo_sender", balance="100.00")
    receiver = create_user("history_combo_receiver", balance="100.00")
    third_user = create_user("history_combo_third", balance="100.00")

    matching_payment = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-combo-1",
    )
    Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("20.00"),
        status="FAILED",
        idempotency_key="history-combo-2",
    )
    Payment.objects.create(
        sender=third_user,
        receiver=sender,
        amount=Decimal("30.00"),
        status="COMPLETED",
        idempotency_key="history-combo-3",
    )

    client = authenticate_client(sender)

    response = client.get(
        reverse("payment-history"),
        {"type": "sent", "status": "COMPLETED"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == matching_payment.id


@pytest.mark.django_db
def test_payment_history_rejects_invalid_type():
    user = create_user("history_invalid_type")

    client = authenticate_client(user)

    response = client.get(reverse("payment-history"), {"type": "weird"})

    assert response.status_code == 400
    assert "type must be one of" in response.data["error"]


@pytest.mark.django_db
def test_payment_history_rejects_invalid_status():
    user = create_user("history_invalid_status")

    client = authenticate_client(user)

    response = client.get(reverse("payment-history"), {"status": "BROKEN"})

    assert response.status_code == 400
    assert "status must be one of" in response.data["error"]


@pytest.mark.django_db
def test_payment_history_rejects_invalid_page():
    user = create_user("history_invalid_page")

    client = authenticate_client(user)

    response = client.get(reverse("payment-history"), {"page": "abc"})

    assert response.status_code == 400
    assert response.data["error"] == "page and page_size must be integers"


@pytest.mark.django_db
def test_payment_history_rejects_invalid_page_size():
    user = create_user("history_invalid_page_size")

    client = authenticate_client(user)

    response = client.get(reverse("payment-history"), {"page_size": "0"})

    assert response.status_code == 400
    assert "page_size must be between 1 and 100" in response.data["error"]


@pytest.mark.django_db
def test_payment_history_filters_by_username():
    user = create_user("alice_filter", balance="100.00")
    bob = create_user("bob_filter", balance="100.00")
    charlie = create_user("charlie_filter", balance="100.00")

    payment1 = Payment.objects.create(
        sender=user,
        receiver=bob,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="username-filter-1",
    )

    Payment.objects.create(
        sender=charlie,
        receiver=user,
        amount=Decimal("15.00"),
        status="COMPLETED",
        idempotency_key="username-filter-2",
    )

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-history"),
        {"username": "bob_filter"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == payment1.id


@pytest.mark.django_db
def test_payment_history_username_not_found_returns_empty():
    user = create_user("alice_empty")

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-history"),
        {"username": "ghost_user"},
    )

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


@pytest.mark.django_db
def test_payment_history_filters_by_date_from():
    user = create_user("date_from_user", balance="100.00")
    other = create_user("date_from_other", balance="100.00")

    payment = Payment.objects.create(
        sender=user,
        receiver=other,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="date-from-1",
    )

    client = authenticate_client(user)

    today = payment.created_at.date().isoformat()

    response = client.get(
        reverse("payment-history"),
        {"date_from": today},
    )

    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_payment_history_contract_includes_expected_top_level_keys():
    user = create_user("history_contract_user", balance="100.00")
    other = create_user("history_contract_other", balance="100.00")

    Payment.objects.create(
        sender=user,
        receiver=other,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-contract-1",
    )

    client = authenticate_client(user)

    response = client.get(reverse("payment-history"))

    assert response.status_code == 200
    assert set(response.data.keys()) == {
        "count",
        "page",
        "page_size",
        "total_pages",
        "type",
        "status",
        "results",
    }


@pytest.mark.django_db
def test_payment_history_contract_result_item_has_expected_keys():
    user = create_user("history_item_user", balance="100.00")
    other = create_user("history_item_other", balance="100.00")

    Payment.objects.create(
        sender=user,
        receiver=other,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-item-1",
    )

    client = authenticate_client(user)

    response = client.get(reverse("payment-history"))

    assert response.status_code == 200
    assert len(response.data["results"]) == 1

    item = response.data["results"][0]

    assert set(item.keys()) == {
        "id",
        "sender",
        "sender_username",
        "receiver",
        "receiver_username",
        "amount",
        "status",
        "idempotency_key",
        "created_at",
        "direction",
        "counterparty_username",
    }


@pytest.mark.django_db
def test_payment_history_contract_keeps_filter_echo_values():
    user = create_user("history_echo_user", balance="100.00")
    other = create_user("history_echo_other", balance="100.00")

    Payment.objects.create(
        sender=user,
        receiver=other,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="history-echo-1",
    )

    client = authenticate_client(user)

    response = client.get(
        reverse("payment-history"),
        {"type": "sent", "status": "COMPLETED"},
    )

    assert response.status_code == 200
    assert response.data["type"] == "sent"
    assert response.data["status"] == "COMPLETED"
    assert response.data["page"] == 1
    assert response.data["page_size"] == 10