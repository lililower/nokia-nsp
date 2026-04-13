import difflib

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.devices.models import Device


@login_required
def debug_hub(request):
    """Debugging tools hub page."""
    devices = Device.objects.all()
    return render(request, "debugging/debug_hub.html", {"devices": devices})


# --- BGP Peers ---

@login_required
def bgp_peers(request, pk):
    device = get_object_or_404(Device, pk=pk)
    peers = []
    error = None
    try:
        from netconf_lib.nokia_routing import get_bgp_peers
        result = get_bgp_peers(device)
        peers = result.get("peers", [])
        error = result.get("error")
    except Exception as e:
        error = str(e)
    return render(request, "debugging/bgp_peers.html", {
        "device": device,
        "peers": peers,
        "error": error,
        "devices": Device.objects.all(),
    })


# --- Route Table ---

@login_required
def route_table(request, pk):
    device = get_object_or_404(Device, pk=pk)
    routes = []
    error = None
    prefix_filter = request.GET.get("prefix", "")
    try:
        from netconf_lib.nokia_routing import get_route_table
        result = get_route_table(device, prefix_filter=prefix_filter or None)
        routes = result.get("routes", [])
        error = result.get("error")
    except Exception as e:
        error = str(e)
    return render(request, "debugging/route_table.html", {
        "device": device,
        "routes": routes,
        "prefix_filter": prefix_filter,
        "error": error,
        "devices": Device.objects.all(),
    })


# --- Port Utilization ---

@login_required
def port_utilization(request, pk):
    device = get_object_or_404(Device, pk=pk)
    ports = []
    error = None
    try:
        from netconf_lib.nokia_port_stats import get_port_utilization
        result = get_port_utilization(device)
        ports = result.get("ports", [])
        error = result.get("error")
    except Exception as e:
        error = str(e)
    return render(request, "debugging/port_utilization.html", {
        "device": device,
        "ports": ports,
        "error": error,
        "devices": Device.objects.all(),
    })


@login_required
def port_utilization_ajax(request, pk):
    """AJAX endpoint for live port stats refresh."""
    device = get_object_or_404(Device, pk=pk)
    try:
        from netconf_lib.nokia_port_stats import get_port_utilization
        result = get_port_utilization(device)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# --- SAP Statistics ---

@login_required
def sap_stats(request, pk):
    device = get_object_or_404(Device, pk=pk)
    saps = []
    error = None
    service_id = request.GET.get("service_id", "")
    try:
        from netconf_lib.nokia_sap_stats import get_sap_statistics
        result = get_sap_statistics(device, service_id=service_id or None)
        saps = result.get("saps", [])
        error = result.get("error")
    except Exception as e:
        error = str(e)
    return render(request, "debugging/sap_stats.html", {
        "device": device,
        "saps": saps,
        "service_id_filter": service_id,
        "error": error,
        "devices": Device.objects.all(),
    })


# --- SDP Bindings ---

@login_required
def sdp_bindings(request, pk):
    device = get_object_or_404(Device, pk=pk)
    sdps = []
    error = None
    try:
        from netconf_lib.nokia_sdp import get_sdp_list
        result = get_sdp_list(device)
        sdps = result.get("sdps", [])
        error = result.get("error")
    except Exception as e:
        error = str(e)
    return render(request, "debugging/sdp_bindings.html", {
        "device": device,
        "sdps": sdps,
        "error": error,
        "devices": Device.objects.all(),
    })


# --- MPLS Path Tracer ---

@login_required
def mpls_trace(request, pk):
    device = get_object_or_404(Device, pk=pk)
    lsps = []
    selected_lsp = None
    error = None
    lsp_name = request.GET.get("lsp", "")
    try:
        from netconf_lib.nokia_mpls import get_lsp_path_detail, get_mpls_lsps
        lsp_result = get_mpls_lsps(device)
        lsps = lsp_result.get("lsps", [])
        error = lsp_result.get("error")
        if lsp_name:
            detail = get_lsp_path_detail(device, lsp_name)
            if not detail.get("error"):
                selected_lsp = detail
            else:
                error = detail.get("error")
    except Exception as e:
        error = str(e)
    return render(request, "debugging/mpls_trace.html", {
        "device": device,
        "lsps": lsps,
        "selected_lsp": selected_lsp,
        "lsp_name": lsp_name,
        "error": error,
        "devices": Device.objects.all(),
    })


# --- LDP Sessions ---

@login_required
def ldp_sessions(request, pk):
    device = get_object_or_404(Device, pk=pk)
    sessions = []
    bindings = []
    statistics = {}
    error = None
    try:
        from netconf_lib.nokia_ldp import get_ldp_bindings, get_ldp_sessions
        session_result = get_ldp_sessions(device)
        sessions = session_result.get("sessions", [])
        statistics = session_result.get("statistics", {})
        error = session_result.get("error")

        binding_result = get_ldp_bindings(device)
        bindings = binding_result.get("bindings", [])
    except Exception as e:
        error = str(e)
    return render(request, "debugging/ldp_sessions.html", {
        "device": device,
        "sessions": sessions,
        "bindings": bindings,
        "statistics": statistics,
        "error": error,
        "devices": Device.objects.all(),
    })


# --- Config Diff ---

@login_required
def config_diff(request, pk):
    device = get_object_or_404(Device, pk=pk)
    diff_html = ""
    error = None
    try:
        from netconf_lib.connection import netconf_connect
        with netconf_connect(device) as mgr:
            running_xml = """
            <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf"/>
            """
            running = mgr.get_config(source="running", filter=("subtree", running_xml))
            candidate = mgr.get_config(source="candidate", filter=("subtree", running_xml))

            running_lines = running.data_xml.splitlines()
            candidate_lines = candidate.data_xml.splitlines()

            differ = difflib.HtmlDiff(wrapcolumn=100)
            diff_html = differ.make_table(
                running_lines, candidate_lines,
                fromdesc="Running Config", todesc="Candidate Config",
                context=True, numlines=3,
            )
    except Exception as e:
        error = str(e)
    return render(request, "debugging/config_diff.html", {
        "device": device,
        "diff_html": diff_html,
        "error": error,
        "devices": Device.objects.all(),
    })
