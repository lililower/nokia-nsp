from xml.etree import ElementTree

from .connection import netconf_connect

NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_sdp_list(device):
    """Fetch Service Distribution Points (SDPs) and their bindings."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <service>
        <sdp/>
      </service>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_sdp_list(result.data_xml)
    except Exception as e:
        return {"error": str(e), "sdps": []}


def _parse_sdp_list(xml_data):
    sdps = []
    try:
        root = ElementTree.fromstring(xml_data)
        for sdp in root.iter(f"{{{NS_STATE}}}sdp"):
            entry = {
                "sdp_id": "",
                "far_end": "",
                "admin_state": "",
                "oper_state": "",
                "delivery_type": "",
                "signaling": "",
                "bound_services": [],
            }
            for child in sdp:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "sdp-id":
                    entry["sdp_id"] = child.text or ""
                elif tag == "far-end":
                    for fc in child:
                        ftag = fc.tag.split("}")[-1] if "}" in fc.tag else fc.tag
                        if ftag == "ip-address":
                            entry["far_end"] = fc.text or ""
                elif tag == "admin-state":
                    entry["admin_state"] = child.text or ""
                elif tag == "oper-state":
                    entry["oper_state"] = child.text or ""
                elif tag == "delivery-type":
                    entry["delivery_type"] = child.text or ""
                elif tag == "signaling":
                    entry["signaling"] = child.text or ""
                elif tag == "binding":
                    for bc in child:
                        btag = bc.tag.split("}")[-1] if "}" in bc.tag else bc.tag
                        if btag == "service-id":
                            entry["bound_services"].append(bc.text or "")
            sdps.append(entry)
    except ElementTree.ParseError:
        pass
    return {"sdps": sdps}
