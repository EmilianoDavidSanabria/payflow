import pytest
import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from services.payment_service import PaymentService
from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db(transaction=True)
def test_concurrent_payments():
    sender = User.objects.create_user(username="sender_concurrent", password="pass")
    receiver = User.objects.create_user(username="receiver_concurrent", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("0.00")
    receiver.wallet.save(update_fields=["balance"])

    def make_payment():
      try:
          PaymentService.create_payment(
              sender=sender,
              receiver=receiver,
              amount=Decimal("60.00"),
              idempotency_key=str(threading.get_ident()),
          )
      except Exception:
          pass

    t1 = threading.Thread(target=make_payment)
    t2 = threading.Thread(target=make_payment)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()

    assert sender.wallet.balance in [Decimal("40.00"), Decimal("100.00")]
    assert receiver.wallet.balance in [Decimal("60.00"), Decimal("0.00")]
    assert sender.wallet.balance >= Decimal("0.00")
    assert Payment.objects.count() <= 1