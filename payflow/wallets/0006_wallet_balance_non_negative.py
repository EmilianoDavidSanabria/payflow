from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0005_alter_wallet_currency'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name='wallet_balance_non_negative',
            ),
        ),
    ]