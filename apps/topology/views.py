import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from apps.devices.models import Device
from .builder import build_topology
from .models import TopologySnapshot


@login_required
def topology_map(request):
    """Main topology map page."""
    devices = Device.objects.all()
    latest_snapshot = TopologySnapshot.objects.first()
    return render(request, "topology/topology_map.html", {
        "devices": devices,
        "latest_snapshot": latest_snapshot,
    })


@login_required
def topology_data(request):
    """AJAX endpoint returning topology graph as JSON.

    Optional query params:
    - device: comma-separated device PKs to include (default: all)
    - cached: "1" to return last snapshot instead of live poll
    """
    use_cached = request.GET.get("cached") == "1"

    if use_cached:
        snapshot = TopologySnapshot.objects.first()
        if snapshot:
            return JsonResponse(snapshot.topology_json)
        # Fall through to live poll if no cache

    device_param = request.GET.get("device", "")
    device_ids = None
    if device_param:
        try:
            device_ids = [int(pk) for pk in device_param.split(",") if pk.strip()]
        except ValueError:
            pass

    try:
        graph = build_topology(device_ids=device_ids)

        # Save snapshot
        TopologySnapshot.objects.create(
            topology_json=graph,
            device_count=graph["stats"]["device_count"],
            tunnel_count=graph["stats"]["total_ldp_sessions"],
        )

        # Keep only last 10 snapshots
        old_snapshots = TopologySnapshot.objects.all()[10:]
        for s in old_snapshots:
            s.delete()

        return JsonResponse(graph)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
