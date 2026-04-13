from django.urls import path

from . import views

urlpatterns = [
    path("", views.service_list, name="service_list"),
    path("create/", views.service_create, name="service_create"),
    path("<int:pk>/", views.service_detail, name="service_detail"),
    path("<int:pk>/deploy/", views.service_deploy, name="service_deploy"),
    path("<int:pk>/confirm/", views.service_confirm, name="service_confirm"),
    path("<int:pk>/cancel-confirm/", views.service_cancel_confirm, name="service_cancel_confirm"),
    path("<int:pk>/delete-deploy/", views.service_delete_deploy, name="service_delete_deploy"),
    path("logs/", views.deployment_logs, name="deployment_logs"),
    path("interface-search/<int:pk>/", views.interface_search_ajax, name="interface_search_ajax"),
]
