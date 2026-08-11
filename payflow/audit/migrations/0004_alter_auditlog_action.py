from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0003_alter_auditlog_action'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('PAYMENT_CREATED', 'Payment Created'),
                    ('PAYMENT_COMPLETED', 'Payment Completed'),
                    ('WALLET_UPDATED', 'Wallet Updated'),
                    ('PAYMENT_REQUEST_CREATED', 'Payment Request Created'),
                    ('PAYMENT_REQUEST_ACCEPTED', 'Payment Request Accepted'),
                    ('PAYMENT_REQUEST_REJECTED', 'Payment Request Rejected'),
                    ('WALLET_TOP_UP_CREATED', 'Wallet Top Up Created'),
                    ('WALLET_TOP_UP_COMPLETED', 'Wallet Top Up Completed'),
                    ('WALLET_TOP_UP_FAILED', 'Wallet Top Up Failed'),
                    ('WALLET_WITHDRAWAL_CREATED', 'Wallet Withdrawal Created'),
                    ('WALLET_WITHDRAWAL_COMPLETED', 'Wallet Withdrawal Completed'),
                    ('PAYMENT_INTENT_CREATED', 'Payment Intent Created'),
                    ('PAYMENT_CHECKOUT_CREATED', 'Payment Checkout Created'),
                    ('PAYMENT_APPROVED', 'Payment Approved'),
                    ('PAYMENT_FAILED', 'Payment Failed'),
                    ('PAYMENT_RECONCILED', 'Payment Reconciled'),
                    ('WEBHOOK_RECEIVED', 'Webhook Received'),
                ],
                max_length=50,
            ),
        ),
    ]