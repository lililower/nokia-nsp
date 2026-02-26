import os

from jinja2 import Environment, FileSystemLoader
from ncclient.operations.rpc import RPCError

from .connection import netconf_connect

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "netconf_templates")
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)


def create_vpls(device, service_id, service_name, customer_id, saps=None, description=""):
    """Deploy a VPLS service to a device via NETCONF edit-config."""
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
            mgr.commit()
            return {"status": "success", "config_sent": config_xml, "response": "Committed"}
        except RPCError as e:
            mgr.discard_changes()
            return {"status": "failed", "config_sent": config_xml, "response": str(e)}


def delete_vpls(device, service_id):
    """Remove a VPLS service from a device."""
    template = _env.get_template("vpls_delete.xml")
    config_xml = template.render(service_id=service_id)
    with netconf_connect(device) as mgr:
        try:
            mgr.edit_config(target="candidate", config=config_xml)
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
