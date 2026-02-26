from django.contrib import admin
from django.urls import include, path

from apps.monitoring.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("accounts/", include("apps.accounts.urls")),
    path("devices/", include("apps.devices.urls")),
    path("services/", include("apps.services.urls")),
    path("monitoring/", include("apps.monitoring.urls")),
]
