from contextlib import contextmanager

from ncclient import manager


@contextmanager
def netconf_connect(device):
    """Context manager for NETCONF sessions to Nokia SR OS devices."""
    conn = manager.connect(
        host=device.hostname,
        port=device.port,
        username=device.username,
        password=device.get_password(),
        hostkey_verify=False,
        device_params={"name": "alu"},
        timeout=30,
    )
    try:
        yield conn
    finally:
        conn.close_session()
