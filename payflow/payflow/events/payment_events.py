from workers.payment_tasks import send_payment_notification
from workers.webhook_tasks import dispatch_webhook

def payment_completed_event(payment):

    send_payment_notification.delay(payment.id)

def payment_completed_event(payment):

    payload = {
        "payment_id": payment.id,
        "amount": str(payment.amount),
        "sender": payment.sender.id,
        "receiver": payment.receiver.id,
    }

    dispatch_webhook.delay(
        "payment_completed",
        payload
    )