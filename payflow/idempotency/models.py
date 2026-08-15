from django.conf import settings
from django.db import models


class IdempotencyKey(models.Model):
    """
    Cachea la respuesta de una operación identificada por una
    Idempotency-Key HTTP, por usuario.

    Estados:
      PROCESSING -> la operación fue admitida y se está ejecutando ahora
                     mismo (o se interrumpió sin terminar). No hay
                     response_body/response_code todavía.
      COMPLETED  -> la operación terminó y devolvió una respuesta 2xx/3xx.
                     La respuesta cacheada se puede servir indefinidamente.
      FAILED     -> la operación terminó con un error determinístico de
                     negocio (ej: saldo insuficiente, monto inválido). La
                     respuesta cacheada se puede servir indefinidamente:
                     un reintento con la misma key + mismos datos debe
                     seguir fallando igual.

    Un fallo TRANSITORIO (timeout, bug, error de infraestructura) nunca
    llega a este modelo con status FAILED: el registro se borra
    (ver IdempotencyService.discard_record) para permitir que un
    reintento legítimo vuelva a intentar desde cero.
    """

    STATUS_PROCESSING = "PROCESSING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
    )

    key = models.CharField(max_length=255)

    request_path = models.CharField(max_length=255)

    request_method = models.CharField(max_length=10)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PROCESSING,
    )

    response_code = models.IntegerField(null=True, blank=True)

    response_body = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key"],
                name="idempotency_unique_user_key",
            ),
        ]

    def __str__(self):
        return f"IdempotencyKey user={self.user_id} key={self.key} status={self.status}"