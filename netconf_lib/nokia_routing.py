from xml.etree import ElementTree

from .connection import netconf_connect

NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_route_table(device, prefix_filter=None):
    """Fetch IPv4 unicast route table from the Base router."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <route-table>
          <unicast>
            <ipv4>
              <route/>
            </ipv4>
          </unicast>
        </route-table>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_route_table(result.data_xml, prefix_filter)
    except Exception as e:
        return {"error": str(e), "routes": []}


def _parse_route_table(xml_data, prefix_filter=None):
    routes = []
    try:
        root = ElementTree.fromstring(xml_data)
        for route in root.iter(f"{{{NS_STATE}}}route"):
            entry = {
                "prefix": "",
                "next_hop": "",
                "protocol": "",
                "preference": "",
                "metric": "",
                "active": False,
            }
            for child in route:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "ip-prefix":
                    entry["prefix"] = child.text or ""
                elif tag == "next-hop":
                    for nhc in child:
                        nhtag = nhc.tag.split("}")[-1] if "}" in nhc.tag else nhc.tag
                        if nhtag == "ip-address":
                            entry["next_hop"] = nhc.text or ""
                elif tag == "route-type":
                    entry["protocol"] = child.text or ""
                elif tag == "preference":
                    entry["preference"] = child.text or ""
                elif tag == "metric":
                    entry["metric"] = child.text or ""
                elif tag == "active":
                    entry["active"] = (child.text or "").lower() == "true"
            if prefix_filter and prefix_filter not in entry["prefix"]:
                continue
            routes.append(entry)
    except ElementTree.ParseError:
        pass
    return {"routes": routes}


def get_bgp_peers(device):
    """Fetch BGP neighbor/peer status."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <bgp>
          <neighbor/>
        </bgp>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_bgp_peers(result.data_xml)
    except Exception as e:
        return {"error": str(e), "peers": []}


def _parse_bgp_peers(xml_data):
    peers = []
    try:
        root = ElementTree.fromstring(xml_data)
        for neighbor in root.iter(f"{{{NS_STATE}}}neighbor"):
            entry = {
                "peer_address": "",
                "peer_as": "",
                "local_as": "",
                "state": "",
                "uptime": "",
                "received_routes": 0,
                "sent_routes": 0,
                "active_routes": 0,
                "description": "",
            }
            for child in neighbor:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "peer-address" or tag == "ip-address":
                    entry["peer_address"] = child.text or ""
                elif tag == "peer-as":
                    entry["peer_as"] = child.text or ""
                elif tag == "local-as":
                    entry["local_as"] = child.text or ""
                elif tag == "session-state":
                    entry["state"] = child.text or ""
                elif tag == "up-time":
                    entry["uptime"] = child.text or ""
                elif tag == "description":
                    entry["description"] = child.text or ""
                elif tag == "statistics":
                    for stat in child:
                        stag = stat.tag.split("}")[-1] if "}" in stat.tag else stat.tag
                        if stag == "received-routes":
                            entry["received_routes"] = int(stat.text or 0)
                        elif stag == "sent-routes":
                            entry["sent_routes"] = int(stat.text or 0)
                        elif stag == "active-routes":
                            entry["active_routes"] = int(stat.text or 0)
            peers.append(entry)
    except ElementTree.ParseError:
        pass
    return {"peers": peers}


def get_system_ip(device):
    """Get the system interface IP (router-id) of a device."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <router>
        <router-name>Base</router-name>
        <interface>
          <interface-name>system</interface-name>
        </interface>
      </router>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            root = ElementTree.fromstring(result.data_xml)
            for child in root.iter(f"{{{NS_STATE}}}ipv4"):
                for sub in child:
                    tag = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
                    if tag == "primary":
                        for addr in sub:
                            atag = addr.tag.split("}")[-1] if "}" in addr.tag else addr.tag
                            if atag == "address":
                                return {"system_ip": addr.text or ""}
            return {"system_ip": ""}
    except Exception as e:
        return {"error": str(e), "system_ip": ""}
