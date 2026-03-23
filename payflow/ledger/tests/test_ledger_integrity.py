import pytest

from ledger.models import LedgerEntry
from services.ledger_service import LedgerService


@pytest.mark.django_db
def test_ledger_balance():

    # crear transfer ficticia
    # verificar que debit == credit

    entries = LedgerEntry.objects.all()

    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)

    assert total_debit == total_credit