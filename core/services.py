from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal

from .models import Session, Registration, Payment


class RegistrationError(Exception):
    pass


def create_registration(*, session: Session, full_name: str, email: str) -> Registration:
    """
    Creates a Registration with guardrails:
    - future session only
    - no duplicates per session+email
    - capacity not exceeded (pending+confirmed)
    """
    now = timezone.now()
    if session.start_at <= now:
        raise RegistrationError("This session is already in the past. Registration is closed.")

    email_norm = email.strip().lower()
    name_norm = " ".join(full_name.strip().split())

    with transaction.atomic():
        # Lock session row to reduce race conditions under concurrency
        session_locked = Session.objects.select_for_update().get(pk=session.pk)

        # Duplicate check
        if Registration.objects.filter(session=session_locked, email=email_norm).exists():
            raise RegistrationError("This email is already registered for this session.")

        # Capacity check (count pending+confirmed; ignore cancelled)
        taken = Registration.objects.filter(
            session=session_locked,
        ).filter(~Q(status=Registration.Status.CANCELLED)).count()

        if taken >= session_locked.capacity:
            raise RegistrationError("This session is full.")

        reg = Registration.objects.create(
            session=session_locked,
            full_name=name_norm,
            email=email_norm,
            status=Registration.Status.PENDING,
        )
        return reg

class PaymentError(Exception):
    pass


def pay_registration(*, registration: Registration, amount: Decimal, provider: str = "mock") -> Payment:
    """
    Mock payment flow:
    - refuse cancelled
    - if already confirmed, return last PAID payment (idempotent-ish)
    - create Payment INITIATED -> PAID
    - move registration to CONFIRMED
    """
    if registration.status == Registration.Status.CANCELLED:
        raise PaymentError("Cannot pay for a cancelled registration.")

    with transaction.atomic():
        reg = Registration.objects.select_for_update().get(pk=registration.pk)

        # If already confirmed, don't create duplicates: return a PAID payment if one exists.
        existing_paid = reg.payments.filter(status=Payment.Status.PAID).order_by("-created_at").first()
        if reg.status == Registration.Status.CONFIRMED and existing_paid:
            return existing_paid

        # Prevent paying twice even if status isn't confirmed yet (e.g., retries)
        existing_initiated = reg.payments.filter(
            Q(status=Payment.Status.INITIATED) | Q(status=Payment.Status.PAID)
        ).order_by("-created_at").first()

        if existing_initiated and existing_initiated.status == Payment.Status.PAID:
            reg.status = Registration.Status.CONFIRMED
            reg.save(update_fields=["status", "updated_at"])
            return existing_initiated

        payment = Payment.objects.create(
            registration=reg,
            amount=amount,
            status=Payment.Status.INITIATED,
            provider=provider,
            reference=f"mock-{reg.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        )

        # Mock gateway success: immediately mark paid
        payment.status = Payment.Status.PAID
        payment.save(update_fields=["status", "updated_at"])

        reg.status = Registration.Status.CONFIRMED
        reg.save(update_fields=["status", "updated_at"])

        return payment
