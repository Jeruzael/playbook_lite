from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("programs/<int:program_id>/", views.program_detail, name="program_detail"),

    path("sessions/<int:session_id>/register/", views.register_for_session, name="register_for_session"),
    path("registrations/<int:registration_id>/success/", views.registration_success, name="registration_success"),
    path("registrations/<int:registration_id>/cancel/", views.cancel_registration, name="cancel_registration"),
    path("registrations/<int:registration_id>/pay/", views.pay, name="pay"),
    path("payments/<int:payment_id>/success/", views.payment_success, name="payment_success"),
]
