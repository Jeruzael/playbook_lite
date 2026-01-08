# pyright: reportIncompatibleVariableOverride=false
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Organization(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    def __str__(self) -> str:
        return self.name
    
class Program(TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_program_name_per_org",                
            )
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"])
        ]

    def __str__(self) -> str:
        return f"{self.organization.name} - {self.name}"
    
class Session(TimeStampedModel):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="sessions")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    location = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['start_at']
        indexes = [
            models.Index(fields=["program", "start_at"]),
            models.Index(fields=["start_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.program.name} @ {timezone.localtime(self.start_at).strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def is_future(self) -> bool:
        return self.start_at >= timezone.now()
    
class Registration(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="registrations")
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "email"],
                name="uniq_registration_per_session_email",
            )
        ]
        indexes = [
            models.Index(fields=["session", "status"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email}) - {self.session}"

class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)

    # for later: stripe session id, gcash ref, etc.
    provider = models.CharField(max_length=50, default="mock", blank=True)
    reference = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["registration", "status"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self) -> str:
        return f"{self.registration.email} — {self.amount} — {self.status}"
    

class WebhookEndpoint(TimeStampedModel):
    """
    Represents a low-code automation endpoint (Zapier/Make/n8n/custom).
    """
    name = models.CharField(max_length=120)
    url = models.URLField()
    is_active = models.BooleanField(default=True)

    # list of event types this endpoint wants, e.g. ["registration.created", "payment.paid"]
    subscribed_events = models.JSONField(default=list, blank=True)

    # optional per-endpoint signing secret (recommended)
    signing_secret = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"


class OutboxEvent(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DELIVERED = "DELIVERED", "Delivered"
        RETRY = "RETRY", "Retry"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name="outbox_events")
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)

    next_attempt_at = models.DateTimeField(default=timezone.now)
    delivered_at = models.DateTimeField(null=True, blank=True)

    last_error = models.TextField(blank=True)
    last_status_code = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "next_attempt_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} -> {self.endpoint.name} [{self.status}]"