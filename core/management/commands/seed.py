from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.models import Organization, Program, Session


class Command(BaseCommand):
    help = "Seed the database with sample Organization, Program, and Sessions."

    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(
            name="Playbook Lite Club",
            defaults={"email": "club@example.com", "phone": "0917-000-0000"},
        )

        program, _ = Program.objects.get_or_create(
            organization=org,
            name="U12 Basketball",
            defaults={"description": "Intro program for kids under 12", "is_active": True},
        )

        now = timezone.now()
        sessions_to_create = []
        for i in range(1, 6):
            start = now + timedelta(days=i)
            end = start + timedelta(hours=2)
            sessions_to_create.append(
                Session(
                    program=program,
                    start_at=start,
                    end_at=end,
                    capacity=20,
                    location="Main Gym",
                )
            )

        # Avoid duplicates: only create if none exist
        if not program.sessions.exists():
            Session.objects.bulk_create(sessions_to_create)
            self.stdout.write(self.style.SUCCESS("Seeded sessions."))
        else:
            self.stdout.write(self.style.WARNING("Sessions already exist; skipping."))

        self.stdout.write(self.style.SUCCESS("Seed complete."))
