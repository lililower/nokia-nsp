from xml.etree import ElementTree

from .connection import netconf_connect

NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_mpls_lsps(device):
    """Fetch MPLS LSP information with paths and statistics."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <mpls>
          <lsp/>
        </mpls>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_mpls_lsps(result.data_xml)
    except Exception as e:
        return {"error": str(e), "lsps": []}


def _parse_mpls_lsps(xml_data):
    lsps = []
    try:
        root = ElementTree.fromstring(xml_data)
        for lsp in root.iter(f"{{{NS_STATE}}}lsp"):
            entry = {
                "lsp_name": "",
                "from_address": "",
                "to_address": "",
                "admin_state": "",
                "oper_state": "",
                "metric": "",
                "path_hops": [],
                "forwarded_packets": 0,
                "forwarded_octets": 0,
            }
            for child in lsp:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "lsp-name":
                    entry["lsp_name"] = child.text or ""
                elif tag == "from":
                    entry["from_address"] = child.text or ""
                elif tag == "to":
                    entry["to_address"] = child.text or ""
                elif tag == "admin-state":
                    entry["admin_state"] = child.text or ""
                elif tag == "oper-state":
                    entry["oper_state"] = child.text or ""
                elif tag == "metric":
                    entry["metric"] = child.text or ""
                elif tag == "path":
                    for hop in child.iter(f"{{{NS_STATE}}}hop"):
                        hop_addr = ""
                        for hc in hop:
                            htag = hc.tag.split("}")[-1] if "}" in hc.tag else hc.tag
                            if htag == "address":
                                hop_addr = hc.text or ""
                        if hop_addr:
                            entry["path_hops"].append(hop_addr)
                elif tag == "statistics":
                    for stat in child:
                        stag = stat.tag.split("}")[-1] if "}" in stat.tag else stat.tag
                        if stag == "forwarded-packets":
                            entry["forwarded_packets"] = int(stat.text or 0)
                        elif stag == "forwarded-octets":
                            entry["forwarded_octets"] = int(stat.text or 0)
            lsps.append(entry)
    except ElementTree.ParseError:
        pass
    return {"lsps": lsps}


def get_mpls_tunnels(device):
    """Fetch MPLS tunnel table (active tunnels with endpoints)."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <tunnel-table/>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_tunnels(result.data_xml)
    except Exception as e:
        return {"error": str(e), "tunnels": []}


def _parse_tunnels(xml_data):
    tunnels = []
    try:
        root = ElementTree.fromstring(xml_data)
        for tunnel in root.iter(f"{{{NS_STATE}}}tunnel"):
            entry = {
                "destination": "",
                "tunnel_id": "",
                "protocol": "",
                "next_hop": "",
                "metric": "",
                "oper_state": "",
            }
            for child in tunnel:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "destination":
                    entry["destination"] = child.text or ""
                elif tag == "tunnel-id":
                    entry["tunnel_id"] = child.text or ""
                elif tag == "protocol":
                    entry["protocol"] = child.text or ""
                elif tag == "next-hop":
                    entry["next_hop"] = child.text or ""
                elif tag == "metric":
                    entry["metric"] = child.text or ""
                elif tag == "oper-state":
                    entry["oper_state"] = child.text or ""
            tunnels.append(entry)
    except ElementTree.ParseError:
        pass
    return {"tunnels": tunnels}


def get_lsp_path_detail(device, lsp_name):
    """Fetch detailed path information for a specific LSP."""
    filter_xml = f"""
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <mpls>
          <lsp>
            <lsp-name>{lsp_name}</lsp-name>
          </lsp>
        </mpls>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            parsed = _parse_mpls_lsps(result.data_xml)
            lsps = parsed.get("lsps", [])
            return lsps[0] if lsps else {"error": f"LSP '{lsp_name}' not found"}
    except Exception as e:
        return {"error": str(e)}
