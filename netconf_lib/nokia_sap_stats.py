from xml.etree import ElementTree

from .connection import netconf_connect

NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"


def get_sap_statistics(device, service_id=None):
    """Fetch SAP ingress/egress statistics for VPLS services."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <service>
        <vpls>
          <sap>
            <statistics/>
          </sap>
        </vpls>
      </service>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_sap_stats(result.data_xml, service_id)
    except Exception as e:
        return {"error": str(e), "saps": []}


def _parse_sap_stats(xml_data, service_id=None):
    saps = []
    try:
        root = ElementTree.fromstring(xml_data)
        current_service_id = ""

        for vpls in root.iter(f"{{{NS_STATE}}}vpls"):
            for child in vpls:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "service-id":
                    current_service_id = child.text or ""
                elif tag == "sap":
                    entry = {
                        "service_id": current_service_id,
                        "sap_id": "",
                        "ingress_packets": 0,
                        "ingress_octets": 0,
                        "egress_packets": 0,
                        "egress_octets": 0,
                        "ingress_dropped": 0,
                        "egress_dropped": 0,
                    }
                    for sap_child in child:
                        stag = sap_child.tag.split("}")[-1] if "}" in sap_child.tag else sap_child.tag
                        if stag == "sap-id":
                            entry["sap_id"] = sap_child.text or ""
                        elif stag == "statistics":
                            for stat in sap_child:
                                stat_tag = stat.tag.split("}")[-1] if "}" in stat.tag else stat.tag
                                if stat_tag == "ingress-packets":
                                    entry["ingress_packets"] = int(stat.text or 0)
                                elif stat_tag == "ingress-octets":
                                    entry["ingress_octets"] = int(stat.text or 0)
                                elif stat_tag == "egress-packets":
                                    entry["egress_packets"] = int(stat.text or 0)
                                elif stat_tag == "egress-octets":
                                    entry["egress_octets"] = int(stat.text or 0)
                                elif stat_tag == "ingress-dropped-packets":
                                    entry["ingress_dropped"] = int(stat.text or 0)
                                elif stat_tag == "egress-dropped-packets":
                                    entry["egress_dropped"] = int(stat.text or 0)

                    if service_id and entry["service_id"] != str(service_id):
                        continue
                    saps.append(entry)
    except ElementTree.ParseError:
        pass
    return {"saps": saps}
