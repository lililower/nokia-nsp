from django.db import models


class TopologySnapshot(models.Model):
    """Cached topology graph data to avoid polling all devices on every page load."""
    created_at = models.DateTimeField(auto_now_add=True)
    topology_json = models.JSONField()
    device_count = models.IntegerField(default=0)
    tunnel_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Topology snapshot at {self.created_at} ({self.device_count} devices, {self.tunnel_count} tunnels)"
