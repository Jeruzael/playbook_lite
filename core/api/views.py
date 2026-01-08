from django.db.models import Count, Q, F
from django.db.models.functions import Greatest
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Program, Session, Registration
from core.services import RegistrationError, create_registration
from .serializers import (
    ProgramSerializer,
    SessionSerializer,
    RegistrationCreateSerializer,
    RegistrationSerializer,
)


class ProgramListAPI(generics.ListAPIView):
    queryset = Program.objects.select_related("organization").filter(is_active=True)
    serializer_class = ProgramSerializer


class ProgramDetailAPI(generics.RetrieveAPIView):
    queryset = Program.objects.select_related("organization").filter(is_active=True)
    serializer_class = ProgramSerializer


class ProgramSessionsAPI(generics.ListAPIView):
    serializer_class = SessionSerializer

    def get_queryset(self):
        program_id = self.kwargs["program_id"]
        # annotate taken/available so clients can show seat info without extra calls
        return (
            Session.objects.select_related("program", "program__organization")
            .filter(program_id=program_id)
            .annotate(
                taken=Count(
                    "registrations",
                    filter=~Q(registrations__status=Registration.Status.CANCELLED),
                ),
            )
            .annotate(
                available=Greatest(F("capacity") - F("taken"), 0),
            )
            .order_by("start_at")
        )


@api_view(["GET"])
def session_availability_api(request, session_id: int):
    qs = (
        Session.objects.filter(id=session_id)
        .annotate(
            taken=Count(
                "registrations",
                filter=~Q(registrations__status=Registration.Status.CANCELLED),
            )
        )
        .annotate(available=Greatest(F("capacity") - F("taken"), 0))
    )
    session = qs.first()
    if not session:
        return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response(
        {
            "session_id": session.id,
            "capacity": session.capacity,
            "taken": session.taken,
            "available": session.available,
        }
    )


class RegistrationCreateAPI(generics.GenericAPIView):
    serializer_class = RegistrationCreateSerializer

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        session_id = ser.validated_data["session_id"]
        full_name = ser.validated_data["full_name"]
        email = ser.validated_data["email"]

        session = Session.objects.select_related("program", "program__organization").filter(id=session_id).first()
        if not session:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            reg = create_registration(session=session, full_name=full_name, email=email)
        except RegistrationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RegistrationSerializer(reg).data, status=status.HTTP_201_CREATED)
