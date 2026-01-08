from django.urls import path
from .views import (
    ProgramListAPI,
    ProgramDetailAPI,
    ProgramSessionsAPI,
    session_availability_api,
    RegistrationCreateAPI,
)

urlpatterns = [
    path("programs/", ProgramListAPI.as_view(), name="api_programs"),
    path("programs/<int:pk>/", ProgramDetailAPI.as_view(), name="api_program_detail"),
    path("programs/<int:program_id>/sessions/", ProgramSessionsAPI.as_view(), name="api_program_sessions"),
    path("sessions/<int:session_id>/availability/", session_availability_api, name="api_session_availability"),
    path("registrations/", RegistrationCreateAPI.as_view(), name="api_registration_create"),
]
