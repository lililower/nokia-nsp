from django.urls import path

from . import views

urlpatterns = [
    path("", views.device_list, name="device_list"),
    path("add/", views.device_create, name="device_create"),
    path("<int:pk>/", views.device_detail, name="device_detail"),
    path("<int:pk>/edit/", views.device_edit, name="device_edit"),
    path("<int:pk>/delete/", views.device_delete, name="device_delete"),
    path("<int:pk>/test/", views.device_test, name="device_test"),
]
