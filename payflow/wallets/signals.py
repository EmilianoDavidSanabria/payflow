from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from wallets.models import Wallet

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance, balance=0, currency="ARS")