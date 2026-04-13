from xml.etree import ElementTree

from .connection import netconf_connect

NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_ldp_sessions(device):
    """Fetch LDP session information from device."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <ldp>
          <session/>
          <statistics/>
        </ldp>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_ldp_sessions(result.data_xml)
    except Exception as e:
        return {"error": str(e), "sessions": [], "statistics": {}}


def _parse_ldp_sessions(xml_data):
    sessions = []
    statistics = {}
    try:
        root = ElementTree.fromstring(xml_data)

        for session in root.iter(f"{{{NS_STATE}}}session"):
            entry = {
                "peer_address": "",
                "local_address": "",
                "state": "",
                "adjacency_type": "",
                "uptime": "",
                "sent_labels": 0,
                "received_labels": 0,
            }
            for child in session:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "peer-address":
                    entry["peer_address"] = child.text or ""
                elif tag == "local-address":
                    entry["local_address"] = child.text or ""
                elif tag == "session-state":
                    entry["state"] = child.text or ""
                elif tag == "adjacency-type":
                    entry["adjacency_type"] = child.text or ""
                elif tag == "up-time":
                    entry["uptime"] = child.text or ""
                elif tag == "statistics":
                    for stat in child:
                        stat_tag = stat.tag.split("}")[-1] if "}" in stat.tag else stat.tag
                        if stat_tag == "sent-label-bindings":
                            entry["sent_labels"] = int(stat.text or 0)
                        elif stat_tag == "received-label-bindings":
                            entry["received_labels"] = int(stat.text or 0)
            sessions.append(entry)

        for stats_elem in root.iter(f"{{{NS_STATE}}}statistics"):
            for child in stats_elem:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "active-sessions":
                    statistics["active_sessions"] = int(child.text or 0)
                elif tag == "active-targeted-sessions":
                    statistics["active_targeted"] = int(child.text or 0)
                elif tag == "active-link-adjacencies":
                    statistics["active_link_adj"] = int(child.text or 0)
            break  # Only the top-level statistics element

    except ElementTree.ParseError:
        pass
    return {"sessions": sessions, "statistics": statistics}


def get_ldp_bindings(device):
    """Fetch active LDP FEC-to-label bindings."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <ldp>
          <bindings>
            <active/>
          </bindings>
        </ldp>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_ldp_bindings(result.data_xml)
    except Exception as e:
        return {"error": str(e), "bindings": []}


def _parse_ldp_bindings(xml_data):
    bindings = []
    try:
        root = ElementTree.fromstring(xml_data)
        for binding in root.iter(f"{{{NS_STATE}}}active"):
            entry = {
                "fec_prefix": "",
                "ingress_label": "",
                "egress_label": "",
                "next_hop": "",
                "peer": "",
            }
            for child in binding:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "fec-prefix":
                    entry["fec_prefix"] = child.text or ""
                elif tag == "ingress-label":
                    entry["ingress_label"] = child.text or ""
                elif tag == "egress-label":
                    entry["egress_label"] = child.text or ""
                elif tag == "next-hop":
                    entry["next_hop"] = child.text or ""
                elif tag == "peer":
                    entry["peer"] = child.text or ""
            bindings.append(entry)
    except ElementTree.ParseError:
        pass
    return {"bindings": bindings}
