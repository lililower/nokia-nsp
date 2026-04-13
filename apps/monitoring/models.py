from django.db import models


class DeviceHealthScore(models.Model):
    """Tracks device health scores over time based on log ID 90 analysis."""
    device = models.ForeignKey("devices.Device", on_delete=models.CASCADE, related_name="health_scores")
    score = models.IntegerField(help_text="Health score 0-100 (100 = healthy)")
    critical_count = models.IntegerField(default=0)
    major_count = models.IntegerField(default=0)
    minor_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    total_events = models.IntegerField(default=0)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_at"]
        verbose_name = "Device Health Score"

    def __str__(self):
        return f"{self.device.name}: {self.score}/100 at {self.checked_at}"

    @property
    def status_label(self):
        if self.score >= 80:
            return "healthy"
        elif self.score >= 50:
            return "degraded"
        else:
            return "critical"
