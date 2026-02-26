from django.conf import settings
from django.db import models


class VPLSService(models.Model):
    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("deployed", "Deployed"),
        ("failed", "Failed"),
        ("deleted", "Deleted"),
    ]

    service_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    customer_id = models.IntegerField()
    description = models.TextField(blank=True)
    devices = models.ManyToManyField("devices.Device", blank=True, related_name="vpls_services")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_services"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "VPLS Service"

    def __str__(self):
        return f"VPLS {self.service_id} - {self.name}"


class ServiceSAP(models.Model):
    service = models.ForeignKey(VPLSService, on_delete=models.CASCADE, related_name="saps")
    device = models.ForeignKey("devices.Device", on_delete=models.CASCADE)
    port = models.CharField(max_length=50, help_text="e.g. 1/1/1")
    vlan = models.IntegerField()

    class Meta:
        unique_together = ("service", "device", "port", "vlan")

    def __str__(self):
        return f"{self.port}:{self.vlan} on {self.device.name}"


class DeploymentLog(models.Model):
    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    service = models.ForeignKey(VPLSService, on_delete=models.CASCADE, related_name="deployment_logs")
    device = models.ForeignKey("devices.Device", on_delete=models.CASCADE)
    action = models.CharField(max_length=20)  # create / delete / modify
    config_sent = models.TextField()
    response = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    deployed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} VPLS {self.service.service_id} on {self.device.name} [{self.status}]"
