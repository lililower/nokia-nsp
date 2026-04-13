from django.urls import path

from . import views

urlpatterns = [
    path("", views.debug_hub, name="debug_hub"),
    path("bgp/<int:pk>/", views.bgp_peers, name="debug_bgp"),
    path("routes/<int:pk>/", views.route_table, name="debug_routes"),
    path("port-util/<int:pk>/", views.port_utilization, name="debug_port_util"),
    path("port-util/<int:pk>/ajax/", views.port_utilization_ajax, name="debug_port_util_ajax"),
    path("sap-stats/<int:pk>/", views.sap_stats, name="debug_sap_stats"),
    path("sdp/<int:pk>/", views.sdp_bindings, name="debug_sdp"),
    path("mpls-trace/<int:pk>/", views.mpls_trace, name="debug_mpls_trace"),
    path("ldp/<int:pk>/", views.ldp_sessions, name="debug_ldp"),
    path("config-diff/<int:pk>/", views.config_diff, name="debug_config_diff"),
]
