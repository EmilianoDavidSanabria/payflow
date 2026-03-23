import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from wallets.models import WalletTransaction

User = get_user_model()


def build_url(transaction_id):
    return f"/wallets/me/transactions/{transaction_id}/"


@pytest.mark.django_db
def test_get_wallet_transaction_detail_success(authenticated_client, wallet):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount="100.00",
        transaction_type="TOP_UP",
        status="COMPLETED",
        rail="SANDBOX",
        provider_status="approved",
        external_reference="ext-123",
    )


    response = authenticated_client.get(build_url(tx.id))

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == tx.id
    assert str(data["amount"]) in {"100.00", "100"}
    assert data["transaction_type"] == "TOP_UP"
    assert data["status"] == "COMPLETED"
    assert data["rail"] == "SANDBOX"
    assert data["provider_status"] == "approved"
    assert data["external_reference"] == "ext-123"
    assert data["wallet_id"] == wallet.id


@pytest.mark.django_db
def test_get_wallet_transaction_not_found(authenticated_client):
    response = authenticated_client.get(build_url(999999))
    assert response.status_code == 404


@pytest.mark.django_db
def test_cannot_access_other_user_transaction(api_client, wallet, django_user_model):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount="100.00",
        transaction_type="TOP_UP",
        status="COMPLETED",
        rail="SANDBOX",
    )

    other_user = django_user_model.objects.create_user(
        username="other_wallet_user",
        password="pass12345",
    )
    api_client.force_authenticate(other_user)

    response = api_client.get(build_url(tx.id))

    assert response.status_code in (403, 404)


@pytest.mark.django_db
def test_failed_transaction_includes_failure_reason(authenticated_client, wallet):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount="100.00",
        transaction_type="TOP_UP",
        status="FAILED",
        rail="MERCADO_PAGO",
        failure_reason="card_declined",
    )

    response = authenticated_client.get(build_url(tx.id))

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "FAILED"
    assert data["failure_reason"] == "card_declined"


@pytest.mark.django_db
def test_pending_transaction_with_checkout(authenticated_client, wallet):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount="200.00",
        transaction_type="TOP_UP",
        status="PENDING",
        rail="MERCADO_PAGO",
        checkout_url="https://checkout.test",
    )

    response = authenticated_client.get(build_url(tx.id))

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "PENDING"
    assert data["checkout_url"] == "https://checkout.test"

    if "can_resume_checkout" in data:
        assert data["can_resume_checkout"] is True


@pytest.mark.django_db
def test_completed_at_field(authenticated_client, wallet):
    completed_time = timezone.now()

    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount="150.00",
        transaction_type="WITHDRAWAL",
        status="COMPLETED",
        rail="SANDBOX",
        completed_at=completed_time,
    )

    response = authenticated_client.get(build_url(tx.id))

    assert response.status_code == 200

    data = response.json()
    assert data["completed_at"] is not None


@pytest.mark.django_db
def test_null_optional_fields(authenticated_client, wallet):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        amount="50.00",
        transaction_type="TOP_UP",
        status="PENDING",
        rail="SANDBOX",
    )

    response = authenticated_client.get(build_url(tx.id))

    assert response.status_code == 200

    data = response.json()
    assert data["failure_reason"] in (None, "")
    assert data["external_reference"] in (None, "")
    assert data["provider_status"] in ("NOT_APPLICABLE", None, "")