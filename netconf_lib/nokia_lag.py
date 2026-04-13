from xml.etree import ElementTree

from .connection import netconf_connect

NS_CONF = "urn:nokia.com:sros:ns:yang:sr:conf"
NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_lag_config(device):
    """Fetch LAG configuration including descriptions and member ports."""
    filter_xml = """
    <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf">
      <lag/>
    </configure>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get_config(source="running", filter=("subtree", filter_xml))
            return _parse_lag_config(result.data_xml)
    except Exception as e:
        return {"error": str(e), "lags": []}


def _parse_lag_config(xml_data):
    lags = []
    try:
        root = ElementTree.fromstring(xml_data)
        for lag in root.iter(f"{{{NS_CONF}}}lag"):
            entry = {
                "lag_id": "",
                "description": "",
                "admin_state": "",
                "mode": "",
                "member_ports": [],
            }
            for child in lag:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "lag-id":
                    entry["lag_id"] = child.text or ""
                elif tag == "description":
                    entry["description"] = child.text or ""
                elif tag == "admin-state":
                    entry["admin_state"] = child.text or ""
                elif tag == "mode":
                    entry["mode"] = child.text or ""
                elif tag == "port":
                    # Member port entries
                    for port_child in child:
                        ptag = port_child.tag.split("}")[-1] if "}" in port_child.tag else port_child.tag
                        if ptag == "port-id":
                            entry["member_ports"].append(port_child.text or "")
            lags.append(entry)
    except ElementTree.ParseError:
        pass
    return {"lags": lags}


def get_lag_state(device):
    """Fetch LAG operational state."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <lag/>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_lag_state(result.data_xml)
    except Exception as e:
        return {"error": str(e), "lags": []}


def _parse_lag_state(xml_data):
    lags = []
    try:
        root = ElementTree.fromstring(xml_data)
        for lag in root.iter(f"{{{NS_STATE}}}lag"):
            entry = {
                "lag_id": "",
                "oper_state": "",
                "active_members": 0,
                "total_members": 0,
                "speed": "",
            }
            for child in lag:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "lag-id":
                    entry["lag_id"] = child.text or ""
                elif tag == "oper-state":
                    entry["oper_state"] = child.text or ""
                elif tag == "active-port-count":
                    entry["active_members"] = int(child.text or 0)
                elif tag == "configured-port-count":
                    entry["total_members"] = int(child.text or 0)
                elif tag == "speed":
                    entry["speed"] = child.text or ""
            lags.append(entry)
    except ElementTree.ParseError:
        pass
    return {"lags": lags}
