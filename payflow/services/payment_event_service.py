from audit.models import AuditLog


class PaymentEventService:

    @staticmethod
    def log_event(action, entity_id, metadata=None):

        AuditLog.objects.create(
            action=action,
            entity_type="wallet_transaction",
            entity_id=entity_id,
            metadata=metadata or {},
        )