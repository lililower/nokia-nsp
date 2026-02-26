from xml.etree import ElementTree

from .connection import netconf_connect


def get_interfaces(device):
    """Fetch interface descriptions and operational status."""
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
        for port in root.iter("{urn:nokia.com:sros:ns:yang:sr:state}port"):
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
