from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fill missing user emails with a deterministic local placeholder"

    def handle(self, *args, **options):
        User = get_user_model()

        users = User.objects.filter(email__isnull=True) | User.objects.filter(email="")

        updated = 0

        for user in users.distinct():
            user.email = f"{user.username}@payflow.local"
            user.save(update_fields=["email"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Backfill complete. Updated {updated} user(s).")
        )