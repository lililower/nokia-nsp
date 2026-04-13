from xml.etree import ElementTree

from .connection import netconf_connect

NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_port_utilization(device):
    """Fetch port statistics for utilization calculation."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <port/>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_port_stats(result.data_xml)
    except Exception as e:
        return {"error": str(e), "ports": []}


def _parse_port_stats(xml_data):
    ports = []
    try:
        root = ElementTree.fromstring(xml_data)
        for port in root.iter(f"{{{NS_STATE}}}port"):
            entry = {
                "port_id": "",
                "description": "",
                "admin_state": "",
                "oper_state": "",
                "speed": "",
                "in_octets": 0,
                "out_octets": 0,
                "in_packets": 0,
                "out_packets": 0,
                "in_errors": 0,
                "out_errors": 0,
                "in_discards": 0,
                "out_discards": 0,
            }
            for child in port:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "port-id":
                    entry["port_id"] = child.text or ""
                elif tag == "description":
                    entry["description"] = child.text or ""
                elif tag == "admin-state":
                    entry["admin_state"] = child.text or ""
                elif tag == "oper-state":
                    entry["oper_state"] = child.text or ""
                elif tag == "ethernet":
                    for ec in child:
                        etag = ec.tag.split("}")[-1] if "}" in ec.tag else ec.tag
                        if etag == "speed":
                            entry["speed"] = ec.text or ""
                elif tag == "statistics":
                    for stat in child:
                        stag = stat.tag.split("}")[-1] if "}" in stat.tag else stat.tag
                        if stag == "in-octets":
                            entry["in_octets"] = int(stat.text or 0)
                        elif stag == "out-octets":
                            entry["out_octets"] = int(stat.text or 0)
                        elif stag == "in-packets":
                            entry["in_packets"] = int(stat.text or 0)
                        elif stag == "out-packets":
                            entry["out_packets"] = int(stat.text or 0)
                        elif stag == "in-errors":
                            entry["in_errors"] = int(stat.text or 0)
                        elif stag == "out-errors":
                            entry["out_errors"] = int(stat.text or 0)
                        elif stag == "in-discards":
                            entry["in_discards"] = int(stat.text or 0)
                        elif stag == "out-discards":
                            entry["out_discards"] = int(stat.text or 0)
            ports.append(entry)
    except ElementTree.ParseError:
        pass
    return {"ports": ports}
