import os
from datetime import timedelta

import attr


@attr.s
class ConfigClass(object):
    """
    All settings can be set via Environment variables.
    If you use pipenv, you are encouraged to use the .env file.
    See pipenv's documentation for more information.
    """

    data_dir: str = attr.ib(default=os.getenv("DATA_DIR", "../data"))
    """
    @param data_dir: Environment: DATA_DIR.
           Directory to save persistent data in.
    @type  data_dir: C{unicode}
    """

    # Web
    web_endpoint: str = attr.ib(
        default=os.getenv("WEB_ENDPOINT", r"tcp6:interface=\:\::port=8080")
    )
    """
    @param web_endpoint: Environment: WEB_ENDPOINT.
           Where we should listen for HTTP connections.
           This defaults to TCP port 8080, but you can also use a UNIX socket,
           which you can proxy from your web server.

           See:
           https://docs.twisted.org/en/stable/core/howto/endpoints.html#servers
           https://klein.readthedocs.io/en/latest/examples/alternativerunning.html#example-ipv6-tls-unix-sockets-endpoints
    @type  web_endpoint: C{unicode} -- Endpoint string
    """

    web_static_dir: str = attr.ib(default=os.getenv("WEB_STATIC_DIR", "../static"))
    """
    @param web_static_dir: Environment: WEB_STATIC_DIR.
           Directory to server static files from.
    @type  web_static_dir: C{unicode}
    """

    # SSH
    ssh_enabled: bool = attr.ib(default=os.getenv("SSH_ENABLED", "YES") != "")
    """
    @param ssh_enabled: Environment: SSH_ENABLED.
           If this environment variable is anything other than empty,
           SSH_ENDPOINT will be used to listen for SSH connections.
    @type  ssh_enabled: C{unicode}
    """

    ssh_endpoint: str = attr.ib(
        default=os.getenv("SSH_ENDPOINT", r"tcp6:interface=\:\::port=2222")
    )
    """
    @param ssh_endpoint: Environment: SSH_ENDPOINT.
           Where we should listen for SSH connections if SSH_ENABLED is
           anything other than empty.

           See:
           https://docs.twisted.org/en/stable/core/howto/endpoints.html#servers
           https://klein.readthedocs.io/en/latest/examples/alternativerunning.html#example-ipv6-tls-unix-sockets-endpoints
    @type  ssh_endpoint: C{unicode} -- Endpoint string
    """

    ssh_key_size: int = attr.ib(default=int(os.getenv("SSH_KEY_SIZE", "4096")))
    """
    @param ssh_key_size: Environment: SSH_KEY_SIZE.
           Size for server's auto-generated SSH host key.
    @type  ssh_key_size: C{unicode}
    """

    ssh_keys_dir: str = attr.ib(default=os.getenv("SSH_KEYS_DIR", "../data/ssh"))
    """
    @param ssh_keys_dir: Environment: SSH_KEYS_DIR.
           Directory to save SSH keys in.
           This includes the server private key and users' public keys.
    @type  ssh_keys_dir: C{unicode}
    """

    # Alerts processing
    new_incident_timeout: timedelta = attr.ib(
        default=timedelta(minutes=int(os.getenv("NEW_INCIDENT_TIMEOUT", "60")))
    )
    """
    @param new_incident_timeout: Environment: NEW_INCIDENT_TIMEOUT.
           Alerts incoming at roughly the same time are grouped into incidents.
           Use this to configure the timeout after which alerts will be
           considered separate incidents, in minutes.
           Example: If it is set for 30 minutes, and alerts come at 09:00,
           09:20, 09:40, and 11:00, then the first 3 will be the same incident and
           the last one will begin a new incident.
           Default value: 60 (i.e. 1 hour).
    """


Config = ConfigClass()

if __name__ == "__main__":
    import inspect
    import sys

    target = "dotenv.example"
    if len(sys.argv) > 1:
        target = sys.argv[1]

    sc = inspect.getsource(ConfigClass).split("\n")[2:]

    with open(target, "w") as f:
        f.write(
            "\n".join(
                [
                    "#",
                    "# Automatically generated, manual changes will be lost",
                    "# Run: python -m adlermanager.Config dotenv.example",
                    "#",
                    "# If using Pipenv or similar, you probably want:",
                    "# To load the adlermanager module:",
                    'PYTHONPATH="./src"',
                    "# To instruct mypy to find the adlermanager module:",
                    'MYPYPATH="./src"',
                    "",
                    "",
                ]
            )
        )
        in_doc = False
        for line in sc:
            if line.strip() == '"""':
                in_doc = not in_doc
                continue
            if "@type" in line:
                continue

            if in_doc or line.strip().startswith("#"):
                if "@param" in line:
                    f.write(f"# {line.split(':', 1)[1].strip()}")
                else:
                    f.write(f"# {line[min(4, len(line)):].strip()}".strip())
                f.write("\n")
            if not in_doc and "getenv" in line:
                parts = line.split('"')
                f.write("\n")
                f.write(f'#{parts[1]}="{parts[3]}"')
                f.write("\n#\n")
