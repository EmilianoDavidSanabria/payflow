import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_existing_idempotency_keys(apps, schema_editor):
    """
    IdempotencyKey es una caché de request/response, no un registro
    contable: no representa dinero ni es fuente de verdad de ninguna
    operación financiera (eso vive en Payment, WalletTransaction y
    LedgerEntry). Los registros existentes fueron creados bajo el
    esquema viejo, donde la key era única globalmente y no estaba
    asociada a ningún usuario, así que no hay forma segura de
    backfillear a qué usuario pertenece cada uno.

    Borrarlos es seguro: en el peor caso, una Idempotency-Key que un
    cliente reintente justo después de este deploy no encontrará la
    respuesta cacheada y la operación se re-evaluará de cero (lo cual,
    para una operación ya completada, es detectada de todas formas por
    las unique constraints de negocio como Payment.idempotency_key).
    """
    IdempotencyKey = apps.get_model("idempotency", "IdempotencyKey")
    IdempotencyKey.objects.all().delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("idempotency", "0002_rename_endpoint_idempotencykey_request_path_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="idempotencykey",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="idempotency_keys",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="idempotencykey",
            name="status",
            field=models.CharField(
                choices=[
                    ("PROCESSING", "Processing"),
                    ("COMPLETED", "Completed"),
                    ("FAILED", "Failed"),
                ],
                default="PROCESSING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="idempotencykey",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        # Borra los registros viejos ANTES de exigir `user` no nulo y
        # antes de crear la unique constraint (user, key): así no hay
        # filas legacy que puedan violarla.
        migrations.RunPython(
            delete_existing_idempotency_keys,
            reverse_code=noop_reverse,
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="idempotency_keys",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="key",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="response_code",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="idempotencykey",
            name="response_body",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="idempotencykey",
            constraint=models.UniqueConstraint(
                fields=["user", "key"],
                name="idempotency_unique_user_key",
            ),
        ),
    ]