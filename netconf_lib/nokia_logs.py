from xml.etree import ElementTree

from .connection import netconf_connect

NS = {"nokia": "urn:nokia.com:sros:ns:yang:sr:state"}

# Severity weights for health score calculation
SEVERITY_WEIGHTS = {
    "critical": 30,
    "major": 10,
    "minor": 3,
    "warning": 1,
}


def get_log_entries(device, log_id=90):
    """Fetch log entries for a specific log ID from device via NETCONF."""
    filter_xml = f"""
    <state xmlns="urn:nokia.com:sros:ns:yang:sr:state">
      <log>
        <log-id>
          <name>{log_id}</name>
        </log-id>
      </log>
    </state>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get(filter=("subtree", filter_xml))
            return _parse_log_entries(result.data_xml)
    except Exception as e:
        return {"error": str(e), "entries": []}


def _parse_log_entries(xml_data):
    """Parse log XML into structured entries."""
    entries = []
    try:
        root = ElementTree.fromstring(xml_data)
        for event in root.iter("{urn:nokia.com:sros:ns:yang:sr:state}event"):
            entry = {
                "sequence": "",
                "timestamp": "",
                "severity": "",
                "application": "",
                "event_id": "",
                "subject": "",
                "message": "",
            }
            for child in event:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "sequence-number":
                    entry["sequence"] = child.text or ""
                elif tag == "timestamp":
                    entry["timestamp"] = child.text or ""
                elif tag == "severity":
                    entry["severity"] = (child.text or "").lower()
                elif tag == "application":
                    entry["application"] = child.text or ""
                elif tag == "event-id":
                    entry["event_id"] = child.text or ""
                elif tag == "subject":
                    entry["subject"] = child.text or ""
                elif tag == "message":
                    entry["message"] = child.text or ""
            entries.append(entry)
    except ElementTree.ParseError:
        pass
    return {"entries": entries}


def calculate_health_score(log_entries):
    """Calculate a device health score from 0-100 based on log severities.

    100 = perfectly healthy (no issues)
    Lower scores indicate more/worse problems.

    Scoring: start at 100, subtract points per severity:
      - critical: -30 per event
      - major: -10 per event
      - minor: -3 per event
      - warning: -1 per event
    Floor at 0.
    """
    score = 100
    severity_counts = {"critical": 0, "major": 0, "minor": 0, "warning": 0}

    for entry in log_entries:
        severity = entry.get("severity", "").lower()
        if severity in severity_counts:
            severity_counts[severity] += 1
            score -= SEVERITY_WEIGHTS.get(severity, 0)

    return {
        "score": max(0, score),
        "severity_counts": severity_counts,
        "total_events": len(log_entries),
    }
