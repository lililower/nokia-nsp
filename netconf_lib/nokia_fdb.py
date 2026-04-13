from xml.etree import ElementTree

from .connection import netconf_connect

NS_STATE = "urn:nokia.com:sros:ns:yang:sr:state"
NS_CONF = "urn:nokia.com:sros:ns:yang:sr:conf"


def _get_all_vpls_service_ids(mgr):
    """Get all VPLS service IDs from running config."""
    filter_xml = """
    <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf">
      <service>
        <vpls/>
      </service>
    </configure>
    """
    result = mgr.get_config(source="running", filter=("subtree", filter_xml))
    root = ElementTree.fromstring(result.data_xml)
    service_ids = []
    for vpls_el in root.iter(f"{{{NS_CONF}}}vpls"):
        sid_el = vpls_el.find(f"{{{NS_CONF}}}service-name")
        if sid_el is None:
            sid_el = vpls_el.find(f"{{{NS_CONF}}}service-id")
        if sid_el is not None and sid_el.text:
            service_ids.append(sid_el.text)
    return service_ids


def _get_fdb_for_service(mgr, service_name):
    """Get FDB entries for a specific VPLS service."""
    filter_xml = f"""
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <service>
        <vpls>
          <service-name>{service_name}</service-name>
          <fdb/>
        </vpls>
      </service>
    </state>
    """
    result = mgr.get(filter=("subtree", filter_xml))
    return result.data_xml


def get_fdb_table(device, service_id=None):
    """Fetch FDB/MAC table entries from device.

    On Nokia SR OS, FDB is per-service. This function:
    1. If service_id is given, queries only that service's FDB.
    2. Otherwise, discovers all VPLS services first, then collects
       FDB from each one.
    """
    try:
        with netconf_connect(device) as mgr:
            if service_id:
                xml_data = _get_fdb_for_service(mgr, str(service_id))
                return _parse_fdb(xml_data, str(service_id))

            # No service_id: try broad query first (works on some SR OS versions)
            try:
                filter_xml = """
                <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
                  <service>
                    <vpls>
                      <fdb/>
                    </vpls>
                  </service>
                </state>
                """
                result = mgr.get(filter=("subtree", filter_xml))
                parsed = _parse_fdb(result.data_xml)
                if parsed["entries"]:
                    return parsed
            except Exception:
                pass

            # Fallback: iterate each VPLS service
            service_ids = _get_all_vpls_service_ids(mgr)
            if not service_ids:
                return {"entries": [], "services": []}

            all_entries = []
            for sid in service_ids:
                try:
                    xml_data = _get_fdb_for_service(mgr, sid)
                    parsed = _parse_fdb(xml_data, sid)
                    all_entries.extend(parsed["entries"])
                except Exception:
                    continue

            return {"entries": all_entries, "services": service_ids}

    except Exception as e:
        return {"error": str(e), "entries": []}


def _parse_fdb(xml_data, default_service_id=None):
    """Parse FDB XML into structured data."""
    entries = []
    try:
        root = ElementTree.fromstring(xml_data)

        # Walk all VPLS elements to capture service context
        for vpls_el in root.iter(f"{{{NS_STATE}}}vpls"):
            # Try to get the service-name/service-id from the vpls parent
            svc_id = default_service_id or ""
            svc_name_el = vpls_el.find(f"{{{NS_STATE}}}service-name")
            svc_id_el = vpls_el.find(f"{{{NS_STATE}}}service-id")
            if svc_name_el is not None and svc_name_el.text:
                svc_id = svc_name_el.text
            elif svc_id_el is not None and svc_id_el.text:
                svc_id = svc_id_el.text

            for mac_entry in vpls_el.iter(f"{{{NS_STATE}}}mac"):
                entry = {
                    "mac_address": "",
                    "sap": "",
                    "service_id": svc_id,
                    "type": "",
                    "age": "",
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
                    elif tag == "age":
                        entry["age"] = child.text or ""
                entries.append(entry)

        # Fallback: if no vpls-scoped macs found, try flat mac iteration
        if not entries:
            for mac_entry in root.iter(f"{{{NS_STATE}}}mac"):
                entry = {
                    "mac_address": "",
                    "sap": "",
                    "service_id": default_service_id or "",
                    "type": "",
                    "age": "",
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
                    elif tag == "age":
                        entry["age"] = child.text or ""
                entries.append(entry)

    except ElementTree.ParseError:
        pass
    return {"entries": entries}
