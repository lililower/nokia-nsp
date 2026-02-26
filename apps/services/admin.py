from django.contrib import admin

from .models import DeploymentLog, ServiceSAP, VPLSService


class ServiceSAPInline(admin.TabularInline):
    model = ServiceSAP
    extra = 1


@admin.register(VPLSService)
class VPLSServiceAdmin(admin.ModelAdmin):
    list_display = ("service_id", "name", "customer_id", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "service_id")
    inlines = [ServiceSAPInline]


@admin.register(DeploymentLog)
class DeploymentLogAdmin(admin.ModelAdmin):
    list_display = ("service", "device", "action", "status", "deployed_by", "timestamp")
    list_filter = ("status", "action")
