from decimal import Decimal
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from django.urls import reverse
from django.http import HttpRequest, HttpResponse

from .forms import RegistrationCreateForm
from .models import Session, Registration, Payment
from .services import RegistrationError, create_registration, PaymentError, pay_registration

from .models import Program


def home(request):
    programs = (
        Program.objects.select_related("organization")
        .filter(is_active=True)
        .order_by("organization__name", "name")
    )
    return render(request, "core/home.html", {"programs": programs})


def program_detail(request, program_id: int):
    program = get_object_or_404(
        Program.objects.select_related("organization"),
        id=program_id,
        is_active=True,
    )

    # Sessions for this program (future first)
    sessions = program.sessions.order_by("start_at")

    now = timezone.now()
    return render(
        request,
        "core/program_detail.html",
        {"program": program, "sessions": sessions, "now": now},
    )


def register_for_session(request: HttpRequest, session_id: int) -> HttpResponse:
    session = get_object_or_404(
        Session.objects.select_related("program", "program__organization"),
        id=session_id,
    )

    if request.method == "POST":
        form = RegistrationCreateForm(request.POST)
        if form.is_valid():
            try:
                reg = create_registration(
                    session=session,
                    full_name=form.cleaned_data["full_name"],
                    email=form.cleaned_data["email"],
                )
                return redirect("core:registration_success", registration_id=reg.id)
            except RegistrationError as e:
                form.add_error(None, str(e))
    else:
        form = RegistrationCreateForm()

    return render(
        request,
        "core/register.html",
        {"session": session, "form": form},
    )


def registration_success(request: HttpRequest, registration_id: int) -> HttpResponse:
    reg = get_object_or_404(
        Registration.objects.select_related("session", "session__program", "session__program__organization"),
        id=registration_id,
    )
    return render(request, "core/registration_success.html", {"reg": reg})


def cancel_registration(request: HttpRequest, registration_id: int) -> HttpResponse:
    reg = get_object_or_404(Registration, id=registration_id)

    if request.method == "POST":
        reg.status = Registration.Status.CANCELLED
        reg.save(update_fields=["status", "updated_at"])
        return redirect("core:registration_success", registration_id=reg.id)

    return render(request, "core/cancel_registration.html", {"reg": reg})


def pay(request: HttpRequest, registration_id: int) -> HttpResponse:
    reg = get_object_or_404(
        Registration.objects.select_related("session", "session__program", "session__program__organization"),
        id=registration_id,
    )

    # For now: fixed fee, later this comes from Program pricing
    amount = Decimal("199.00")

    if request.method == "POST":
        try:
            payment = pay_registration(registration=reg, amount=amount, provider="mock")
            return redirect("core:payment_success", payment_id=payment.id)
        except PaymentError as e:
            return render(request, "core/payment_error.html", {"reg": reg, "error": str(e)})

    return render(request, "core/pay.html", {"reg": reg, "amount": amount})


def payment_success(request: HttpRequest, payment_id: int) -> HttpResponse:
    payment = get_object_or_404(
        Payment.objects.select_related(
            "registration",
            "registration__session",
            "registration__session__program",
            "registration__session__program__organization",
        ),
        id=payment_id,
    )
    return render(request, "core/payment_success.html", {"payment": payment})
