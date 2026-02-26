from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet


class Device(models.Model):
    STATUS_CHOICES = [
        ("online", "Online"),
        ("offline", "Offline"),
        ("unknown", "Unknown"),
    ]

    name = models.CharField(max_length=100, unique=True)
    hostname = models.CharField(max_length=255, help_text="IP address or FQDN")
    port = models.IntegerField(default=830)
    username = models.CharField(max_length=100)
    encrypted_password = models.BinaryField()
    platform = models.CharField(max_length=50, default="SR-7750")
    sw_version = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unknown")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.hostname})"

    def set_password(self, raw_password):
        f = Fernet(settings.FERNET_KEY.encode() if isinstance(settings.FERNET_KEY, str) else settings.FERNET_KEY)
        self.encrypted_password = f.encrypt(raw_password.encode())

    def get_password(self):
        f = Fernet(settings.FERNET_KEY.encode() if isinstance(settings.FERNET_KEY, str) else settings.FERNET_KEY)
        return f.decrypt(bytes(self.encrypted_password)).decode()
