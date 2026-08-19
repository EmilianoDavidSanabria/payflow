from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0006_wallet_wallet_balance_non_negative'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallettransaction',
            name='provider_payment_id',
            field=models.CharField(blank=True, help_text='ID del pago en el proveedor externo (ej: payment id de Mercado Pago) que efectivamente acreditó/completó esta transacción. Único cuando está presente: el mismo pago del proveedor no puede acreditar dos WalletTransaction distintas.', max_length=255, null=True),
        ),
        migrations.AddConstraint(
            model_name='wallettransaction',
            constraint=models.UniqueConstraint(condition=models.Q(('provider_payment_id__isnull', False)), fields=('provider_payment_id',), name='wallet_transaction_unique_provider_payment_id'),
        ),
    ]