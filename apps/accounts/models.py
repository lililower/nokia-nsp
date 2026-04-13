from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("operator", "Operator"),
        ("viewer", "Viewer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")
    force_password_change = models.BooleanField(
        default=False,
        help_text="Require user to change password on next login.",
    )
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_user"

    def is_admin(self):
        return self.role == "admin"

    def is_operator(self):
        return self.role in ("admin", "operator")

    def is_viewer(self):
        return True

    @property
    def is_locked(self):
        from django.utils import timezone
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("login_failed", "Login Failed"),
        ("deploy", "Deploy Service"),
        ("deploy_confirm", "Confirm Deploy"),
        ("deploy_rollback", "Rollback Deploy"),
        ("deploy_delete", "Delete Service Deploy"),
        ("service_create", "Create Service"),
        ("device_create", "Create Device"),
        ("device_update", "Update Device"),
        ("device_delete", "Delete Device"),
        ("user_create", "Create User"),
        ("password_change", "Password Change"),
        ("health_check", "Health Check"),
        ("config_view", "View Config"),
        ("other", "Other"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_logs",
    )
    username = models.CharField(max_length=150, help_text="Username at time of action (preserved if user deleted)")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    detail = models.TextField(blank=True, help_text="Human-readable description")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    target_object = models.CharField(max_length=200, blank=True, help_text="e.g. 'VPLSService:42', 'Device:3'")

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp", "action"]),
            models.Index(fields=["username"]),
        ]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.username}: {self.action} — {self.detail[:80]}"

    @classmethod
    def log(cls, request, action, detail="", target_object=""):
        """Convenience method to create an audit log entry from a request."""
        user = request.user if request.user.is_authenticated else None
        username = user.username if user else request.POST.get("username", "anonymous")
        ip = cls._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        return cls.objects.create(
            user=user,
            username=username,
            action=action,
            detail=detail,
            ip_address=ip,
            user_agent=user_agent,
            target_object=target_object,
        )

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
