from django.db import models


class IdempotencyKey(models.Model):

    key = models.CharField(max_length=255, unique=True)

    request_path = models.CharField(max_length=255)

    request_method = models.CharField(max_length=10)

    response_code = models.IntegerField()

    response_body = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IdempotencyKey {self.key}"