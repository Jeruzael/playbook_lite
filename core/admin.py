from django.contrib import admin
from .models import Organization, Program, Session, Registration, Payment

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "created_at")
    search_fields = ("name", "email")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "created_at")
    list_filter = ("is_active", "organization")
    search_fields = ("name",)
    autocomplete_fields = ("organization",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("program", "start_at", "end_at", "capacity", "location")
    list_filter = ("program__organization", "program")
    search_fields = ("program__name", "location")
    autocomplete_fields = ("program",)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "session", "status", "created_at")
    list_filter = ("status", "session__program")
    search_fields = ("full_name", "email")
    autocomplete_fields = ("session",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("registration", "amount", "status", "provider", "reference", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("registration__email", "reference")
    autocomplete_fields = ("registration",)
# Register your models here.
