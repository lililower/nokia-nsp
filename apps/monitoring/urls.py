from django.urls import path

from . import views

urlpatterns = [
    path("fdb/", views.fdb_table, name="fdb_table"),
    path("fdb/<int:pk>/ajax/", views.fdb_table_ajax, name="fdb_table_ajax"),
    path("fdb/<int:pk>/export/", views.fdb_export_csv, name="fdb_export_csv"),
    path("interfaces/", views.interface_list, name="interface_list"),
]
