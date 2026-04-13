import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.devices.models import Device
from apps.services.models import DeploymentLog, VPLSService
from .models import DeviceHealthScore


@login_required
def dashboard(request):
    devices = Device.objects.all()[:10]

    # Build device list with health scores attached
    devices_with_health = []
    for device in devices:
        latest_health = device.health_scores.first()
        devices_with_health.append({
            "device": device,
            "health": latest_health,
        })

    context = {
        "device_count": Device.objects.count(),
        "online_count": Device.objects.filter(status="online").count(),
        "service_count": VPLSService.objects.exclude(status="deleted").count(),
        "deployed_count": VPLSService.objects.filter(status="deployed").count(),
        "recent_logs": DeploymentLog.objects.select_related("service", "device", "deployed_by")[:10],
        "devices_with_health": devices_with_health,
    }
    return render(request, "monitoring/dashboard.html", context)


@login_required
def device_health(request):
    """Device health overview page showing all devices and their scores."""
    devices = Device.objects.all()
    device_scores = []
    for device in devices:
        latest = device.health_scores.first()
        history = list(device.health_scores.all()[:10])
        device_scores.append({
            "device": device,
            "latest": latest,
            "history": history,
        })

    return render(request, "monitoring/device_health.html", {
        "device_scores": device_scores,
    })


@login_required
def device_health_detail(request, pk):
    """Detailed health history for a single device."""
    device = get_object_or_404(Device, pk=pk)
    scores = device.health_scores.all()[:50]
    return render(request, "monitoring/device_health_detail.html", {
        "device": device,
        "scores": scores,
    })


@login_required
def device_health_ajax(request, pk):
    """AJAX endpoint to trigger a live health check for a device."""
    device = get_object_or_404(Device, pk=pk)
    try:
        from netconf_lib.nokia_logs import calculate_health_score, get_log_entries
        result = get_log_entries(device, log_id=90)
        if result.get("error"):
            return JsonResponse({"error": result["error"]}, status=500)

        entries = result.get("entries", [])
        health = calculate_health_score(entries)

        # Save the score
        DeviceHealthScore.objects.create(
            device=device,
            score=health["score"],
            critical_count=health["severity_counts"]["critical"],
            major_count=health["severity_counts"]["major"],
            minor_count=health["severity_counts"]["minor"],
            warning_count=health["severity_counts"]["warning"],
            total_events=health["total_events"],
        )

        return JsonResponse({
            "score": health["score"],
            "critical": health["severity_counts"]["critical"],
            "major": health["severity_counts"]["major"],
            "minor": health["severity_counts"]["minor"],
            "warning": health["severity_counts"]["warning"],
            "total_events": health["total_events"],
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def fdb_table(request):
    devices = Device.objects.all()
    selected_device_id = request.GET.get("device")
    entries = []
    interfaces = []
    error = None

    if selected_device_id:
        device = get_object_or_404(Device, pk=selected_device_id)
        try:
            from netconf_lib.nokia_fdb import get_fdb_table
            from netconf_lib.nokia_interfaces import get_interfaces

            fdb_result = get_fdb_table(device)
            iface_result = get_interfaces(device)

            entries = fdb_result.get("entries", [])
            interfaces = iface_result.get("interfaces", [])
            error = fdb_result.get("error") or iface_result.get("error")

            # Build interface description lookup
            desc_map = {i["name"]: i["description"] for i in interfaces}
            for entry in entries:
                sap_port = entry.get("sap", "").split(":")[0] if entry.get("sap") else ""
                entry["interface_desc"] = desc_map.get(sap_port, "")

        except Exception as e:
            error = str(e)

    return render(request, "monitoring/fdb_table.html", {
        "devices": devices,
        "selected_device_id": selected_device_id,
        "entries": entries,
        "interfaces": interfaces,
        "error": error,
    })


@login_required
def fdb_table_ajax(request, pk):
    """AJAX endpoint for refreshing FDB table data."""
    device = get_object_or_404(Device, pk=pk)
    try:
        from netconf_lib.nokia_fdb import get_fdb_table
        from netconf_lib.nokia_interfaces import get_interfaces

        fdb_result = get_fdb_table(device)
        iface_result = get_interfaces(device)

        entries = fdb_result.get("entries", [])
        interfaces = iface_result.get("interfaces", [])

        desc_map = {i["name"]: i["description"] for i in interfaces}
        for entry in entries:
            sap_port = entry.get("sap", "").split(":")[0] if entry.get("sap") else ""
            entry["interface_desc"] = desc_map.get(sap_port, "")

        return JsonResponse({"entries": entries, "interfaces": interfaces})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def fdb_export_csv(request, pk):
    """Export FDB table as CSV."""
    device = get_object_or_404(Device, pk=pk)
    try:
        from netconf_lib.nokia_fdb import get_fdb_table
        from netconf_lib.nokia_interfaces import get_interfaces

        fdb_result = get_fdb_table(device)
        iface_result = get_interfaces(device)

        entries = fdb_result.get("entries", [])
        interfaces = iface_result.get("interfaces", [])
        desc_map = {i["name"]: i["description"] for i in interfaces}
    except Exception:
        entries = []
        desc_map = {}

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="fdb_{device.name}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Interface (SAP)", "Description", "MAC Address", "Service ID", "Type"])
    for entry in entries:
        sap_port = entry.get("sap", "").split(":")[0] if entry.get("sap") else ""
        writer.writerow([
            entry.get("sap", ""),
            desc_map.get(sap_port, ""),
            entry.get("mac_address", ""),
            entry.get("service_id", ""),
            entry.get("type", ""),
        ])
    return response


@login_required
def interface_list(request):
    devices = Device.objects.all()
    selected_device_id = request.GET.get("device")
    interfaces = []
    error = None

    if selected_device_id:
        device = get_object_or_404(Device, pk=selected_device_id)
        try:
            from netconf_lib.nokia_interfaces import get_interfaces
            result = get_interfaces(device)
            interfaces = result.get("interfaces", [])
            error = result.get("error")
        except Exception as e:
            error = str(e)

    return render(request, "monitoring/interface_list.html", {
        "devices": devices,
        "selected_device_id": selected_device_id,
        "interfaces": interfaces,
        "error": error,
    })
