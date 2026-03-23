from audit.models import AuditLog


class AuditService:

    @staticmethod
    def log_action(user, action, entity_type=None, entity_id=None, metadata=None):

        AuditLog.objects.create(
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {}
        )