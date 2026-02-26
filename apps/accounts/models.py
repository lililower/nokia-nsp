from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("operator", "Operator"),
        ("viewer", "Viewer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")

    class Meta:
        db_table = "auth_user"

    def is_admin(self):
        return self.role == "admin"

    def is_operator(self):
        return self.role in ("admin", "operator")

    def is_viewer(self):
        return True
