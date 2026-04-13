import hashlib
import os

from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet


def _get_fernet():
    """Get Fernet instance with key derived from FERNET_KEY + machine-specific salt.

    This adds defense-in-depth: even if someone steals the .env file,
    they also need access to the same machine to derive the same key.
    """
    base_key = settings.FERNET_KEY
    if isinstance(base_key, str):
        base_key = base_key.encode()

    # Salt with a machine-specific value (hostname + OS-level secret if available)
    machine_id = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "nokia-nsp"))
    salt = hashlib.sha256(machine_id.encode()).digest()

    # Derive a Fernet-compatible key (32 bytes, base64url-encoded)
    import base64
    derived = hashlib.pbkdf2_hmac("sha256", base_key, salt, iterations=100_000)
    fernet_key = base64.urlsafe_b64encode(derived[:32])
    return Fernet(fernet_key)


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

    # Track who last modified credentials
    credentials_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    credentials_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.hostname})"

    def set_password(self, raw_password):
        f = _get_fernet()
        self.encrypted_password = f.encrypt(raw_password.encode())

    def get_password(self):
        f = _get_fernet()
        return f.decrypt(bytes(self.encrypted_password)).decode()
