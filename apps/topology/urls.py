from django.urls import path

from . import views

urlpatterns = [
    path("", views.topology_map, name="topology_map"),
    path("data/", views.topology_data, name="topology_data"),
]
