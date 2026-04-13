from django.apps import AppConfig


class DebuggingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.debugging"
    verbose_name = "Debugging"
