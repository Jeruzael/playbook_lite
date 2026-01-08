import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create (or update) a Django superuser from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        enabled = os.getenv("DJANGO_BOOTSTRAP_SUPERUSER", "0") == "1"

        if not enabled:
            self.stdout.write("Bootstrap disabled (DJANGO_BOOTSTRAP_SUPERUSER!=1). Skipping.")
            return

        if not username or not password:
            raise SystemExit("Missing DJANGO_SUPERUSER_USERNAME or DJANGO_SUPERUSER_PASSWORD")

        User = get_user_model()

        user, created = User.objects.get_or_create(username=username, defaults={"email": email or ""})
        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser created: {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser updated: {username}"))
