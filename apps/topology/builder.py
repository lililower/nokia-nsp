import concurrent.futures

from apps.devices.models import Device
from netconf_lib.nokia_interfaces import get_lldp_neighbors
from netconf_lib.nokia_ldp import get_ldp_sessions
from netconf_lib.nokia_mpls import get_mpls_lsps, get_mpls_tunnels
from netconf_lib.nokia_routing import get_system_ip


def build_topology(device_ids=None):
    """Build a full network topology graph from all (or selected) devices.

    Polls devices in parallel using ThreadPoolExecutor.
    Returns a vis.js compatible graph: {nodes: [...], edges: [...], stats: {...}}
    """
    if device_ids:
        devices = list(Device.objects.filter(pk__in=device_ids))
    else:
        devices = list(Device.objects.all())

    if not devices:
        return {"nodes": [], "edges": [], "stats": {}}

    # Poll all devices in parallel
    device_data = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_poll_device, device): device
            for device in devices
        }
        for future in concurrent.futures.as_completed(futures):
            device = futures[future]
            try:
                device_data[device.pk] = future.result()
            except Exception as e:
                device_data[device.pk] = {"error": str(e), "device": device}

    return _assemble_graph(devices, device_data)


def _poll_device(device):
    """Poll a single device for all topology-relevant data."""
    system_ip_result = get_system_ip(device)
    ldp_result = get_ldp_sessions(device)
    mpls_result = get_mpls_lsps(device)
    tunnel_result = get_mpls_tunnels(device)
    lldp_result = get_lldp_neighbors(device)

    return {
        "device": device,
        "system_ip": system_ip_result.get("system_ip", ""),
        "ldp_sessions": ldp_result.get("sessions", []),
        "ldp_stats": ldp_result.get("statistics", {}),
        "mpls_lsps": mpls_result.get("lsps", []),
        "tunnels": tunnel_result.get("tunnels", []),
        "lldp_neighbors": lldp_result.get("neighbors", []),
        "errors": {
            "system_ip": system_ip_result.get("error"),
            "ldp": ldp_result.get("error"),
            "mpls": mpls_result.get("error"),
            "tunnels": tunnel_result.get("error"),
            "lldp": lldp_result.get("error"),
        },
    }


def _assemble_graph(devices, device_data):
    """Assemble vis.js graph from polled device data."""
    nodes = []
    edges = []
    edge_set = set()  # Prevent duplicate edges

    # Build system IP -> device mapping for resolving LDP peer addresses
    ip_to_device = {}
    for pk, data in device_data.items():
        if "error" not in data or data.get("system_ip"):
            ip_to_device[data.get("system_ip", "")] = data["device"]
        # Also map by hostname
        ip_to_device[data["device"].hostname] = data["device"]

    # Create nodes
    for device in devices:
        data = device_data.get(device.pk, {})
        system_ip = data.get("system_ip", "")
        has_errors = any(v for v in data.get("errors", {}).values() if v)

        node = {
            "id": f"device-{device.pk}",
            "label": f"{device.name}\n{system_ip or device.hostname}",
            "title": (
                f"<b>{device.name}</b><br>"
                f"Hostname: {device.hostname}<br>"
                f"System IP: {system_ip or 'N/A'}<br>"
                f"Platform: {device.platform}<br>"
                f"Status: {device.status}<br>"
                f"LDP Sessions: {len(data.get('ldp_sessions', []))}<br>"
                f"MPLS LSPs: {len(data.get('mpls_lsps', []))}"
            ),
            "group": device.status if not has_errors else "error",
            "system_ip": system_ip,
            "device_pk": device.pk,
        }
        nodes.append(node)

    # Create edges from LLDP neighbors (physical links)
    for pk, data in device_data.items():
        device = data.get("device")
        if not device:
            continue
        for neighbor in data.get("lldp_neighbors", []):
            remote_name = neighbor.get("remote_system_name", "")
            # Find the remote device in our inventory
            remote_device = None
            for d in devices:
                if d.name == remote_name or d.hostname == remote_name:
                    remote_device = d
                    break
            if not remote_device:
                continue

            edge_key = tuple(sorted([device.pk, remote_device.pk]))
            edge_id = f"phys-{edge_key[0]}-{edge_key[1]}"
            if edge_id not in edge_set:
                edge_set.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "from": f"device-{device.pk}",
                    "to": f"device-{remote_device.pk}",
                    "label": neighbor.get("local_port", ""),
                    "title": (
                        f"Physical Link<br>"
                        f"Local: {neighbor.get('local_port', '')}<br>"
                        f"Remote: {neighbor.get('remote_port_id', '')}<br>"
                        f"Remote System: {remote_name}"
                    ),
                    "type": "physical",
                    "color": {"color": "#6c757d"},
                    "width": 3,
                    "dashes": False,
                })

    # Create edges from LDP sessions
    for pk, data in device_data.items():
        device = data.get("device")
        if not device:
            continue
        for session in data.get("ldp_sessions", []):
            peer_addr = session.get("peer_address", "")
            remote_device = ip_to_device.get(peer_addr)
            if not remote_device:
                continue

            edge_key = tuple(sorted([device.pk, remote_device.pk]))
            edge_id = f"ldp-{edge_key[0]}-{edge_key[1]}"
            if edge_id not in edge_set:
                edge_set.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "from": f"device-{device.pk}",
                    "to": f"device-{remote_device.pk}",
                    "label": "LDP",
                    "title": (
                        f"LDP Session<br>"
                        f"State: {session.get('state', '')}<br>"
                        f"Type: {session.get('adjacency_type', '')}<br>"
                        f"Uptime: {session.get('uptime', '')}<br>"
                        f"Sent Labels: {session.get('sent_labels', 0)}<br>"
                        f"Recv Labels: {session.get('received_labels', 0)}"
                    ),
                    "type": "ldp",
                    "color": {"color": "#0d6efd"},
                    "width": 2,
                    "dashes": [5, 5],
                })

    # Create edges from MPLS LSPs
    for pk, data in device_data.items():
        device = data.get("device")
        if not device:
            continue
        for lsp in data.get("mpls_lsps", []):
            to_addr = lsp.get("to_address", "")
            remote_device = ip_to_device.get(to_addr)
            if not remote_device:
                continue

            edge_id = f"lsp-{device.pk}-{remote_device.pk}-{lsp.get('lsp_name', '')}"
            if edge_id not in edge_set:
                edge_set.add(edge_id)
                octets = lsp.get("forwarded_octets", 0)
                packets = lsp.get("forwarded_packets", 0)
                edges.append({
                    "id": edge_id,
                    "from": f"device-{device.pk}",
                    "to": f"device-{remote_device.pk}",
                    "label": lsp.get("lsp_name", "LSP"),
                    "title": (
                        f"MPLS LSP: {lsp.get('lsp_name', '')}<br>"
                        f"State: {lsp.get('oper_state', '')}<br>"
                        f"From: {lsp.get('from_address', '')}<br>"
                        f"To: {to_addr}<br>"
                        f"Hops: {' → '.join(lsp.get('path_hops', []))}<br>"
                        f"Fwd Packets: {packets:,}<br>"
                        f"Fwd Octets: {octets:,}"
                    ),
                    "type": "lsp",
                    "color": {"color": "#198754"},
                    "width": 2,
                    "dashes": [10, 5],
                    "arrows": "to",
                })

    tunnel_count = sum(len(d.get("ldp_sessions", [])) for d in device_data.values())
    lsp_count = sum(len(d.get("mpls_lsps", [])) for d in device_data.values())

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "device_count": len(devices),
            "physical_links": sum(1 for e in edges if e["type"] == "physical"),
            "ldp_tunnels": sum(1 for e in edges if e["type"] == "ldp"),
            "mpls_lsps": sum(1 for e in edges if e["type"] == "lsp"),
            "total_ldp_sessions": tunnel_count,
            "total_lsps": lsp_count,
        },
    }
