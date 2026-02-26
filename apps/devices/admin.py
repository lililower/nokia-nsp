from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "hostname", "port", "platform", "status", "updated_at")
    list_filter = ("status", "platform")
    search_fields = ("name", "hostname")
