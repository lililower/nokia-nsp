from django.urls import path

from . import views

urlpatterns = [
    path("", views.service_list, name="service_list"),
    path("create/", views.service_create, name="service_create"),
    path("<int:pk>/", views.service_detail, name="service_detail"),
    path("<int:pk>/deploy/", views.service_deploy, name="service_deploy"),
    path("<int:pk>/delete-deploy/", views.service_delete_deploy, name="service_delete_deploy"),
    path("logs/", views.deployment_logs, name="deployment_logs"),
]
