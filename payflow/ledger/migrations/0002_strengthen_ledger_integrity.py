from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ledgerentry",
            name="reference",
            field=models.CharField(
                db_index=True,
                max_length=255,
            ),
        ),

        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.CheckConstraint(
                name="ledger_entry_non_negative_amounts",
                check=(
                    Q(debit__gte=0)
                    & Q(credit__gte=0)
                ),
            ),
        ),

        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.CheckConstraint(
                name="ledger_entry_exactly_one_side",
                check=(
                    Q(debit__gt=0, credit=0)
                    | Q(credit__gt=0, debit=0)
                ),
            ),
        ),

        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.UniqueConstraint(
                fields=["reference"],
                condition=Q(debit__gt=0),
                name="unique_debit_per_reference",
            ),
        ),

        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.UniqueConstraint(
                fields=["reference"],
                condition=Q(credit__gt=0),
                name="unique_credit_per_reference",
            ),
        ),
    ]