import pytest
from decimal import Decimal
from unittest.mock import patch

from services.payment_reconciliation_service import PaymentReconciliationService
from wallets.models import WalletTransaction
from audit.models import AuditLog


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_completes_pending_payment(
    mp_service_mock,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("100.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_123",
    )

    mp_instance = mp_service_mock.return_value
    mp_instance.search_payment_by_external_reference.return_value = {
        "id": "payment_123",
        "status": "approved",
    }

    PaymentReconciliationService.reconcile_pending_topups()

    wallet.refresh_from_db()
    tx.refresh_from_db()

    assert tx.status == "COMPLETED"
    assert tx.provider_status == "approved"
    assert wallet.balance == Decimal("100.00")

    event = AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_type="wallet_transaction",
        entity_id=tx.id,
    ).latest("created_at")

    assert event.metadata["provider_payment_id"] == "payment_123"
    assert event.metadata["provider_status"] == "approved"
    assert event.metadata["external_reference"] == "payment_123"
    assert event.metadata["result"] == "completed"


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_fails_rejected_payment(
    mp_service_mock,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("50.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_456",
    )

    mp_instance = mp_service_mock.return_value
    mp_instance.search_payment_by_external_reference.return_value = {
        "id": "payment_456",
        "status": "rejected",
        "status_detail": "cc_rejected_other_reason",
    }

    PaymentReconciliationService.reconcile_pending_topups()

    wallet.refresh_from_db()
    tx.refresh_from_db()

    assert tx.status == "FAILED"
    assert tx.provider_status == "rejected"
    assert tx.failure_reason == "cc_rejected_other_reason"
    assert wallet.balance == Decimal("0.00")

    event = AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_type="wallet_transaction",
        entity_id=tx.id,
    ).latest("created_at")

    assert event.metadata["provider_payment_id"] == "payment_456"
    assert event.metadata["provider_status"] == "rejected"
    assert event.metadata["external_reference"] == "payment_456"
    assert event.metadata["failure_reason"] == "cc_rejected_other_reason"
    assert event.metadata["result"] == "failed"


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_fails_cancelled_payment(
    mp_service_mock,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("75.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_cancelled_1",
    )

    mp_instance = mp_service_mock.return_value
    mp_instance.search_payment_by_external_reference.return_value = {
        "id": "mp_cancelled_1",
        "status": "cancelled",
        "status_detail": "user_abandoned",
    }

    PaymentReconciliationService.reconcile_pending_topups()

    wallet.refresh_from_db()
    tx.refresh_from_db()

    assert tx.status == "FAILED"
    assert tx.provider_status == "cancelled"
    assert tx.failure_reason == "user_abandoned"
    assert wallet.balance == Decimal("0.00")

    event = AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_type="wallet_transaction",
        entity_id=tx.id,
    ).latest("created_at")

    assert event.metadata["provider_payment_id"] == "mp_cancelled_1"
    assert event.metadata["provider_status"] == "cancelled"
    assert event.metadata["external_reference"] == "payment_cancelled_1"
    assert event.metadata["failure_reason"] == "user_abandoned"
    assert event.metadata["result"] == "failed"


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_ignores_transaction_without_external_reference(
    mp_service_mock,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("40.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="",
        provider_status="CHECKOUT_CREATED",
    )

    PaymentReconciliationService.reconcile_pending_topups()

    tx.refresh_from_db()
    wallet.refresh_from_db()

    mp_service_mock.return_value.search_payment_by_external_reference.assert_not_called()
    assert tx.status == "PENDING"
    assert tx.provider_status == "CHECKOUT_CREATED"
    assert wallet.balance == Decimal("0.00")
    assert not AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_id=tx.id,
    ).exists()


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_ignores_when_provider_returns_no_payment(
    mp_service_mock,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("60.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_missing_1",
        provider_status="CHECKOUT_CREATED",
    )

    mp_service_mock.return_value.search_payment_by_external_reference.return_value = {}

    PaymentReconciliationService.reconcile_pending_topups()

    tx.refresh_from_db()
    wallet.refresh_from_db()

    assert tx.status == "PENDING"
    assert tx.provider_status == "CHECKOUT_CREATED"
    assert wallet.balance == Decimal("0.00")
    assert not AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_id=tx.id,
    ).exists()


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_updates_provider_status_for_non_terminal_payment(
    mp_service_mock,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("80.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_in_process_1",
        provider_status="CHECKOUT_CREATED",
    )

    mp_service_mock.return_value.search_payment_by_external_reference.return_value = {
        "id": "mp_in_process_1",
        "status": "in_process",
        "status_detail": "pending_contingency",
    }

    PaymentReconciliationService.reconcile_pending_topups()

    tx.refresh_from_db()
    wallet.refresh_from_db()

    assert tx.status == "PENDING"
    assert tx.provider_status == "in_process"
    assert tx.failure_reason in (None, "")
    assert wallet.balance == Decimal("0.00")
    assert not AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_id=tx.id,
    ).exists()


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_does_not_save_provider_status_again_when_it_did_not_change(
    mp_service_mock,
    wallet,
):
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("90.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_same_status_1",
        provider_status="in_process",
    )

    previous_updated_at = tx.updated_at

    mp_service_mock.return_value.search_payment_by_external_reference.return_value = {
        "id": "mp_same_status_1",
        "status": "in_process",
        "status_detail": "pending_review_manual",
    }

    PaymentReconciliationService.reconcile_pending_topups()

    tx.refresh_from_db()

    assert tx.status == "PENDING"
    assert tx.provider_status == "in_process"
    assert tx.updated_at == previous_updated_at
    assert not AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_id=tx.id,
    ).exists()


@pytest.mark.django_db
@patch("services.payment_reconciliation_service.MercadoPagoService")
def test_reconciliation_logs_error_and_continues_with_next_transaction_when_one_fails(
    mp_service_mock,
    wallet,
):
    second_wallet = wallet

    first_tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("30.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_error_1",
        provider_status="CHECKOUT_CREATED",
    )

    second_tx = WalletTransaction.objects.create(
        wallet=second_wallet,
        transaction_type="TOP_UP",
        amount=Decimal("45.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="payment_ok_2",
        provider_status="CHECKOUT_CREATED",
    )

    mp_instance = mp_service_mock.return_value
    mp_instance.search_payment_by_external_reference.side_effect = [
        Exception("temporary mp search failure"),
        {
            "id": "mp_ok_2",
            "status": "approved",
        },
    ]

    PaymentReconciliationService.reconcile_pending_topups()

    first_tx.refresh_from_db()
    second_tx.refresh_from_db()
    second_wallet.refresh_from_db()

    assert first_tx.status == "PENDING"
    assert first_tx.provider_status == "CHECKOUT_CREATED"

    error_event = AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_type="wallet_transaction",
        entity_id=first_tx.id,
    ).latest("created_at")

    assert error_event.metadata["external_reference"] == "payment_error_1"
    assert error_event.metadata["result"] == "error"
    assert error_event.metadata["error"] == "temporary mp search failure"

    assert second_tx.status == "COMPLETED"
    assert second_tx.provider_status == "approved"
    assert second_wallet.balance == Decimal("45.00")

    success_event = AuditLog.objects.filter(
        action="PAYMENT_RECONCILED",
        entity_type="wallet_transaction",
        entity_id=second_tx.id,
    ).latest("created_at")

    assert success_event.metadata["provider_payment_id"] == "mp_ok_2"
    assert success_event.metadata["provider_status"] == "approved"
    assert success_event.metadata["external_reference"] == "payment_ok_2"
    assert success_event.metadata["result"] == "completed"