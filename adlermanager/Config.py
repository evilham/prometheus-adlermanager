import attr
import os
from datetime import timedelta


@attr.s
class ConfigClass(object):
    """
    All settings can be set via Environment variables.
    If you use pipenv, you are encouraged to use the .env file.
    See pipenv's documentation for more information.

    @param data_dir: Environment: DATA_DIR.
           Directory to save persistent data in.
    @type  data_dir: C{unicode}

    @param web_endpoint: Environment: WEB_ENDPOINT.
           Where we should listen for HTTP connections.
    @type  web_endpoint: C{unicode} -- Endpoint string. See twisted docs.

    @param web_static_dir: Environment: WEB_STATIC_DIR.
           Directory to server static files from.
    @type  web_static_dir: C{unicode}

    @param ssh_endpoint: Environment: SSH_ENDPOINT.
           Where we should listen for SSH connections.
    @type  ssh_endpoint: C{unicode} -- Endpoint string. See twisted docs.

    @param ssh_key_size: Environment: SSH_KEY_SIZE.
           Size for server's auto-generated SSH host key.
    @type  ssh_key_size: C{unicode}

    @param ssh_keys_dir: Environment: SSH_KEYS_DIR.
           Directory to save SSH keys in.
           This includes the server private key and users' public keys.
    @type  ssh_keys_dir: C{unicode}

    @param new_incident_timeout: Environment: NEW_INCIDENT_TIMEOUT.
           Alerts incoming at roughly the same time are grouped into incidents.
           Use this to configure the timeout after which alerts will be
           considered separate incidents, in minutes.
           Example: If it is set for 30 minutes, and alerts come at 09:00,
           09:20, 09:40, and 11:00, then the first 3 will be the same incident and
           the last one will begin a new incident.
           Default value: 60 (i.e. 1 hour).
    """

    data_dir = attr.ib(default=os.getenv("DATA_DIR", "../data"))

    # Web
    web_endpoint = attr.ib(default=os.getenv("WEB_ENDPOINT", "unix:adler.socket"))
    web_static_dir = attr.ib(default=os.getenv("WEB_STATIC_DIR", "../static"))

    # SSH
    ssh_enabled = attr.ib(default=os.getenv("SSH_ENABLED", b"") != b"")
    ssh_endpoint = attr.ib(
        default=os.getenv("SSH_ENDPOINT", r"tcp6:interface=\:\::port=2222")
    )
    ssh_key_size = attr.ib(default=int(os.getenv("SSH_KEY_SIZE", "4096")))
    ssh_keys_dir = attr.ib(default=os.getenv("SSH_KEYS_DIR", "../data/ssh"))

    # Alerts processing
    new_incident_timeout = attr.ib(
        default=timedelta(minutes=int(os.getenv("NEW_INCIDENT_TIMEOUT", "60")))
    )


Config = ConfigClass()
