from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
def test_health_endpoint_returns_ok():
    user = User.objects.create_user(username="core_health_user", password="pass")

    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/core/health/")

    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert "message" in response.data


@pytest.mark.django_db
def test_metrics_endpoint_returns_expected_keys():
    user = User.objects.create_user(username="core_metrics_user", password="pass")

    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/core/metrics/")

    assert response.status_code == 200

    assert "total_users" in response.data
    assert "total_wallets" in response.data
    assert "total_payments" in response.data
    assert "total_ledger_entries" in response.data
    assert "total_audit_logs" in response.data

    assert "completed_payments" in response.data
    assert "failed_payments" in response.data
    assert "pending_payments" in response.data
    assert "total_volume_transferred" in response.data
    assert "payments_last_24h" in response.data


@pytest.mark.django_db
def test_metrics_endpoint_returns_business_metrics_values():
    sender = User.objects.create_user(username="metrics_sender", password="pass")
    receiver = User.objects.create_user(username="metrics_receiver", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("50.00")
    receiver.wallet.save(update_fields=["balance"])

    Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="metrics-completed-1",
    )

    Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("20.00"),
        status="COMPLETED",
        idempotency_key="metrics-completed-2",
    )

    Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("30.00"),
        status="FAILED",
        idempotency_key="metrics-failed-1",
    )

    old_pending_payment = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("40.00"),
        status="PENDING",
        idempotency_key="metrics-pending-old-1",
    )

    Payment.objects.filter(id=old_pending_payment.id).update(
        created_at=timezone.now() - timedelta(days=2)
    )

    client = APIClient()
    client.force_authenticate(sender)

    response = client.get("/core/metrics/")

    assert response.status_code == 200
    assert response.data["completed_payments"] == 2
    assert response.data["failed_payments"] == 1
    assert response.data["pending_payments"] == 1
    assert response.data["total_volume_transferred"] == "30.00"
    assert response.data["payments_last_24h"] == 3


@pytest.mark.django_db
def test_dashboard_summary_returns_wallet_recent_summary_and_recent_activity():
    sender = User.objects.create_user(username="core_dash_sender", password="pass")
    receiver = User.objects.create_user(username="core_dash_receiver", password="pass")

    sender.wallet.balance = Decimal("150.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("25.00")
    receiver.wallet.save(update_fields=["balance"])

    sent_payment = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="core-dash-1",
    )

    received_payment = Payment.objects.create(
        sender=receiver,
        receiver=sender,
        amount=Decimal("5.00"),
        status="COMPLETED",
        idempotency_key="core-dash-2",
    )

    client = APIClient()
    client.force_authenticate(sender)

    response = client.get("/core/dashboard-summary/")

    assert response.status_code == 200
    assert "wallet" in response.data
    assert "recent_summary" in response.data
    assert "recent_activity" in response.data

    wallet_data = response.data["wallet"]
    summary = response.data["recent_summary"]
    activity = response.data["recent_activity"]

    assert wallet_data["user"] == sender.id
    assert wallet_data["balance"] == "150.00"
    assert wallet_data["currency"] == "USD"

    assert summary["period_days"] == 30
    assert summary["sent_total"] == "10.00"
    assert summary["received_total"] == "5.00"
    assert summary["sent_count"] == 1
    assert summary["received_count"] == 1

    assert len(activity) == 2

    returned_ids = {item["id"] for item in activity}
    assert returned_ids == {sent_payment.id, received_payment.id}

    first_item = activity[0]
    assert "direction" in first_item
    assert "counterparty_username" in first_item
    assert first_item["direction"] in ["sent", "received"]


@pytest.mark.django_db
def test_dashboard_summary_limits_recent_activity_to_five_items():
    sender = User.objects.create_user(username="core_dash_limit_sender", password="pass")
    receiver = User.objects.create_user(username="core_dash_limit_receiver", password="pass")

    sender.wallet.balance = Decimal("500.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("0.00")
    receiver.wallet.save(update_fields=["balance"])

    for i in range(7):
        Payment.objects.create(
            sender=sender,
            receiver=receiver,
            amount=Decimal("10.00"),
            status="COMPLETED",
            idempotency_key=f"core-dash-limit-{i}",
        )

    client = APIClient()
    client.force_authenticate(sender)

    response = client.get("/core/dashboard-summary/")

    assert response.status_code == 200
    assert len(response.data["recent_activity"]) == 5


@pytest.mark.django_db
def test_dashboard_summary_recent_summary_only_counts_completed_last_30_days():
    sender = User.objects.create_user(username="core_dash_summary_sender", password="pass")
    receiver = User.objects.create_user(username="core_dash_summary_receiver", password="pass")

    sender.wallet.balance = Decimal("500.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("500.00")
    receiver.wallet.save(update_fields=["balance"])

    recent_completed_sent = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("30.00"),
        status="COMPLETED",
        idempotency_key="core-dash-summary-1",
    )

    recent_completed_received = Payment.objects.create(
        sender=receiver,
        receiver=sender,
        amount=Decimal("12.00"),
        status="COMPLETED",
        idempotency_key="core-dash-summary-2",
    )

    old_completed_sent = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("99.00"),
        status="COMPLETED",
        idempotency_key="core-dash-summary-3",
    )

    failed_payment = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("77.00"),
        status="FAILED",
        idempotency_key="core-dash-summary-4",
    )

    Payment.objects.filter(id=old_completed_sent.id).update(
        created_at=timezone.now() - timedelta(days=31)
    )
    Payment.objects.filter(id=failed_payment.id).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    client = APIClient()
    client.force_authenticate(sender)

    response = client.get("/core/dashboard-summary/")

    assert response.status_code == 200
    summary = response.data["recent_summary"]

    assert summary["period_days"] == 30
    assert summary["sent_total"] == "30.00"
    assert summary["received_total"] == "12.00"
    assert summary["sent_count"] == 1
    assert summary["received_count"] == 1


@pytest.mark.django_db
def test_core_endpoints_require_authentication():
    client = APIClient()

    health_response = client.get("/core/health/")
    metrics_response = client.get("/core/metrics/")
    dashboard_response = client.get("/core/dashboard-summary/")

    assert health_response.status_code == 401
    assert metrics_response.status_code == 401
    assert dashboard_response.status_code == 401