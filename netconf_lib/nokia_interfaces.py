from xml.etree import ElementTree

from .connection import netconf_connect

NS_CONF = "urn:nokia.com:sros:ns:yang:sr:conf"
NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_interfaces(device):
    """Fetch interface descriptions and operational status from state."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <port/>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_interfaces(result.data_xml)
    except Exception as e:
        return {"error": str(e), "interfaces": []}


def _parse_interfaces(xml_data):
    """Parse interface XML into structured data."""
    interfaces = []
    try:
        root = ElementTree.fromstring(xml_data)
        for port in root.iter(f"{{{NS_STATE}}}port"):
            iface = {
                "name": "",
                "description": "",
                "admin_status": "",
                "oper_status": "",
                "speed": "",
            }
            for child in port:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "port-id":
                    iface["name"] = child.text or ""
                elif tag == "description":
                    iface["description"] = child.text or ""
                elif tag == "admin-state":
                    iface["admin_status"] = child.text or ""
                elif tag == "oper-state":
                    iface["oper_status"] = child.text or ""
                elif tag == "ethernet":
                    for eth_child in child:
                        eth_tag = eth_child.tag.split("}")[-1] if "}" in eth_child.tag else eth_child.tag
                        if eth_tag == "speed":
                            iface["speed"] = eth_child.text or ""
            interfaces.append(iface)
    except ElementTree.ParseError:
        pass
    return {"interfaces": interfaces}


def get_interface_descriptions(device):
    """Fetch full interface info from both config and state, merged.

    Returns a list of dicts with port_id, description, admin_state, oper_state,
    speed, and lag_member_of.
    """
    config_ports = _get_port_config(device)
    state_ports = get_interfaces(device).get("interfaces", [])

    # Build lookup: port_id -> config data
    config_map = {p["port_id"]: p for p in config_ports}
    state_map = {p["name"]: p for p in state_ports}

    # Merge: config descriptions take precedence, state provides oper data
    all_port_ids = set(config_map.keys()) | set(state_map.keys())
    merged = []
    for port_id in sorted(all_port_ids):
        conf = config_map.get(port_id, {})
        state = state_map.get(port_id, {})
        merged.append({
            "port_id": port_id,
            "description": conf.get("description") or state.get("description", ""),
            "admin_state": conf.get("admin_state") or state.get("admin_status", ""),
            "oper_state": state.get("oper_status", ""),
            "speed": state.get("speed", ""),
            "lag_member_of": conf.get("lag_member_of", ""),
        })
    return merged


def _get_port_config(device):
    """Fetch port configuration (descriptions, LAG membership)."""
    filter_xml = """
    <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf">
      <port/>
    </configure>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get_config(source="running", filter=("subtree", filter_xml))
            return _parse_port_config(result.data_xml)
    except Exception:
        return []


def _parse_port_config(xml_data):
    ports = []
    try:
        root = ElementTree.fromstring(xml_data)
        for port in root.iter(f"{{{NS_CONF}}}port"):
            entry = {
                "port_id": "",
                "description": "",
                "admin_state": "",
                "lag_member_of": "",
            }
            for child in port:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "port-id":
                    entry["port_id"] = child.text or ""
                elif tag == "description":
                    entry["description"] = child.text or ""
                elif tag == "admin-state":
                    entry["admin_state"] = child.text or ""
                elif tag == "ethernet":
                    for ec in child:
                        etag = ec.tag.split("}")[-1] if "}" in ec.tag else ec.tag
                        if etag == "lag":
                            entry["lag_member_of"] = ec.text or ""
            ports.append(entry)
    except ElementTree.ParseError:
        pass
    return ports


def get_lldp_neighbors(device):
    """Fetch LLDP neighbor info for topology discovery."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <port>
        <ethernet>
          <lldp>
            <remote-system/>
          </lldp>
        </ethernet>
      </port>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_lldp(result.data_xml)
    except Exception as e:
        return {"error": str(e), "neighbors": []}


def _parse_lldp(xml_data):
    neighbors = []
    try:
        root = ElementTree.fromstring(xml_data)
        current_port = ""
        for port in root.iter(f"{{{NS_STATE}}}port"):
            for child in port:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "port-id":
                    current_port = child.text or ""
                elif tag == "ethernet":
                    for ec in child:
                        etag = ec.tag.split("}")[-1] if "}" in ec.tag else ec.tag
                        if etag == "lldp":
                            for lldp_child in ec:
                                ltag = lldp_child.tag.split("}")[-1] if "}" in lldp_child.tag else lldp_child.tag
                                if ltag == "remote-system":
                                    neighbor = {
                                        "local_port": current_port,
                                        "remote_system_name": "",
                                        "remote_port_id": "",
                                        "remote_port_desc": "",
                                        "remote_system_desc": "",
                                    }
                                    for rc in lldp_child:
                                        rtag = rc.tag.split("}")[-1] if "}" in rc.tag else rc.tag
                                        if rtag == "system-name":
                                            neighbor["remote_system_name"] = rc.text or ""
                                        elif rtag == "port-id":
                                            neighbor["remote_port_id"] = rc.text or ""
                                        elif rtag == "port-description":
                                            neighbor["remote_port_desc"] = rc.text or ""
                                        elif rtag == "system-description":
                                            neighbor["remote_system_desc"] = rc.text or ""
                                    neighbors.append(neighbor)
    except ElementTree.ParseError:
        pass
    return {"neighbors": neighbors}
