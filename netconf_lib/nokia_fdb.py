from xml.etree import ElementTree

from .connection import netconf_connect

NS = {"nokia": "urn:nokia.com:sros:ns:yang:sr:state"}


def get_fdb_table(device, service_id=None):
    """Fetch FDB/MAC table entries from device."""
    filter_xml = """
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <service>
        <vpls>
          <fdb/>
        </vpls>
      </service>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_fdb(result.data_xml, service_id)
    except Exception as e:
        return {"error": str(e), "entries": []}


def _parse_fdb(xml_data, service_id=None):
    """Parse FDB XML into structured data."""
    entries = []
    try:
        root = ElementTree.fromstring(xml_data)
        for mac_entry in root.iter("{urn:nokia.com:sros:ns:yang:sr:state}mac"):
            entry = {
                "mac_address": "",
                "sap": "",
                "service_id": "",
                "type": "",
            }
            for child in mac_entry:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "address":
                    entry["mac_address"] = child.text or ""
                elif tag == "sap":
                    entry["sap"] = child.text or ""
                elif tag == "service-id":
                    entry["service_id"] = child.text or ""
                elif tag == "type":
                    entry["type"] = child.text or ""
            if service_id and entry["service_id"] != str(service_id):
                continue
            entries.append(entry)
    except ElementTree.ParseError:
        pass
    return {"entries": entries}
