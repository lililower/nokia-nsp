import os

from jinja2 import Environment, FileSystemLoader
from ncclient.operations.rpc import RPCError

from .connection import netconf_connect

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "netconf_templates")
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)


def check_service_exists(device, service_id):
    """Check if a VPLS service ID already exists on the device."""
    filter_xml = f"""
    <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf">
      <service>
        <vpls>
          <service-id>{service_id}</service-id>
        </vpls>
      </service>
    </configure>
    """
    try:
        with netconf_connect(device) as mgr:
            result = mgr.get_config(source="running", filter=("subtree", filter_xml))
            # If the response contains a vpls element with this service-id, it exists
            data = result.data_xml
            return f"<service-id>{service_id}</service-id>" in data
    except Exception:
        # If we can't check, return False to not block (but log the issue)
        return False


def create_vpls(device, service_id, service_name, customer_id, saps=None,
                description="", commit_mode="normal", confirmed_timeout=600):
    """Deploy a VPLS service to a device via NETCONF edit-config.

    Args:
        commit_mode: "normal" for immediate commit, "confirmed" for commit confirmed
        confirmed_timeout: rollback timeout in seconds for commit confirmed (default 600 = 10 min)
    """
    template = _env.get_template("vpls_create.xml")
    config_xml = template.render(
        service_id=service_id,
        service_name=service_name,
        customer_id=customer_id,
        description=description,
        saps=saps or [],
    )
    with netconf_connect(device) as mgr:
        try:
            mgr.edit_config(target="candidate", config=config_xml)

            # Validate before commit
            validate_result = mgr.validate(source="candidate")
            validate_ok = True
            validate_msg = "Validation passed"

            if commit_mode == "confirmed":
                mgr.commit(confirmed=True, timeout=str(confirmed_timeout))
                return {
                    "status": "pending_confirm",
                    "config_sent": config_xml,
                    "response": f"Committed (confirmed, rollback in {confirmed_timeout}s). "
                                f"Validation: {validate_msg}",
                    "validation": validate_msg,
                    "validated": validate_ok,
                }
            else:
                mgr.commit()
                return {
                    "status": "success",
                    "config_sent": config_xml,
                    "response": f"Committed. Validation: {validate_msg}",
                    "validation": validate_msg,
                    "validated": validate_ok,
                }
        except RPCError as e:
            error_msg = str(e)
            # Determine if this was a validation failure or commit failure
            mgr.discard_changes()
            return {
                "status": "failed",
                "config_sent": config_xml,
                "response": error_msg,
                "validation": error_msg,
                "validated": False,
            }


def confirm_commit(device):
    """Send a confirming commit to accept a pending commit confirmed."""
    with netconf_connect(device) as mgr:
        try:
            mgr.commit()
            return {"status": "success", "response": "Commit confirmed accepted."}
        except RPCError as e:
            return {"status": "failed", "response": str(e)}


def cancel_commit(device):
    """Discard pending commit confirmed (triggers immediate rollback)."""
    with netconf_connect(device) as mgr:
        try:
            mgr.discard_changes()
            return {"status": "success", "response": "Commit cancelled, configuration rolled back."}
        except RPCError as e:
            return {"status": "failed", "response": str(e)}


def delete_vpls(device, service_id, commit_mode="normal", confirmed_timeout=600):
    """Remove a VPLS service from a device."""
    template = _env.get_template("vpls_delete.xml")
    config_xml = template.render(service_id=service_id)
    with netconf_connect(device) as mgr:
        try:
            mgr.edit_config(target="candidate", config=config_xml)

            # Validate before commit
            validate_result = mgr.validate(source="candidate")
            validate_msg = "Validation passed"

            if commit_mode == "confirmed":
                mgr.commit(confirmed=True, timeout=str(confirmed_timeout))
                return {
                    "status": "pending_confirm",
                    "config_sent": config_xml,
                    "response": f"Committed (confirmed, rollback in {confirmed_timeout}s). "
                                f"Validation: {validate_msg}",
                }
            else:
                mgr.commit()
                return {"status": "success", "config_sent": config_xml, "response": "Committed"}
        except RPCError as e:
            mgr.discard_changes()
            return {"status": "failed", "config_sent": config_xml, "response": str(e)}


def add_sap(device, service_id, port, vlan):
    """Add a SAP to an existing VPLS service."""
    template = _env.get_template("vpls_sap.xml")
    config_xml = template.render(service_id=service_id, port=port, vlan=vlan)
    with netconf_connect(device) as mgr:
        try:
            mgr.edit_config(target="candidate", config=config_xml)
            mgr.validate(source="candidate")
            mgr.commit()
            return {"status": "success", "config_sent": config_xml, "response": "Committed"}
        except RPCError as e:
            mgr.discard_changes()
            return {"status": "failed", "config_sent": config_xml, "response": str(e)}


def get_vpls_status(device, service_id=None):
    """Retrieve VPLS service status via NETCONF get."""
    filter_xml = """
    <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf">
      <service>
        <vpls/>
      </service>
    </configure>
    """
    with netconf_connect(device) as mgr:
        result = mgr.get_config(source="running", filter=("subtree", filter_xml))
        return result.data_xml
