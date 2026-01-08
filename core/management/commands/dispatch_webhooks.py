from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import OutboxEvent
from core.webhooks import dispatch_one


class Command(BaseCommand):
    help = "Dispatch pending/retry webhook outbox events."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        limit = options["limit"]

        qs = (
            OutboxEvent.objects.select_related("endpoint")
            .filter(status__in=[OutboxEvent.Status.PENDING, OutboxEvent.Status.RETRY])
            .filter(next_attempt_at__lte=timezone.now())
            .order_by("next_attempt_at")[:limit]
        )

        count = 0
        for event in qs:
            dispatch_one(event)
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Dispatched {count} event(s)."))
