from rest_framework import serializers
from core.models import Program, Session, Registration


class ProgramSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Program
        fields = ["id", "organization_name", "name", "description", "is_active"]


class SessionSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source="program.name", read_only=True)
    organization_name = serializers.CharField(source="program.organization.name", read_only=True)

    # these may come from annotation; fallback is handled in getters
    taken = serializers.IntegerField(read_only=True)
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Session
        fields = [
            "id",
            "program",
            "program_name",
            "organization_name",
            "start_at",
            "end_at",
            "capacity",
            "location",
            "taken",
            "available",
        ]


class RegistrationCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ["id", "session", "full_name", "email", "status", "created_at"]
