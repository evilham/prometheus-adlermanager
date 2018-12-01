import attr
import os

@attr.s
class ConfigClass(object):
    """
    All settings can be set via Environment variables.
    If you use pipenv, you are encouraged to use the a .env file.
    See pipenv's documentation for more information.

    @param data_dir: Environment: DATA_DIR.
           Where persistent data will be saved.
    @type  data_dir: C{unicode}

    @param web_endpoint: Environment: WEB_ENDPOINT.
           Where we should listen for HTTP connections.
    @type  web_endpoint: C{unicode} -- Endpoint string. See twisted docs.

    @param web_static_dir: Environment: WEB_STATIC_DIR.
           Where static files are to be found.
    @type  web_static_dir: C{unicode}

    @param ssh_endpoint: Environment: SSH_ENDPOINT.
           Where we should listen for SSH connections.
    @type  ssh_endpoint: C{unicode} -- Endpoint string. See twisted docs.

    @param ssh_key_size: Environment: SSH_KEY_SIZE.
           Size for server's auto-generated SSH key.
    @type  ssh_key_size: C{unicode}

    @param ssh_keys_dir: Environment: SSH_KEYS_DIR.
           Where SSH keys will be saved.
           This includes the server private key and users' public keys.
    @type  ssh_keys_dir: C{unicode}
    """

    data_dir = attr.ib(
            default=os.getenv('DATA_DIR', '../data'))

    # Web
    web_endpoint = attr.ib(
            default=os.getenv('WEB_ENDPOINT', 'unix:adler.socket'))
    web_static_dir = attr.ib(
            default=os.getenv('WEB_STATIC_DIR', '../static'))


    # SSH
    ssh_endpoint = attr.ib(
            default=os.getenv('SSH_ENDPOINT', r'tcp6:interface=\:\::port=2222'))
    ssh_key_size = attr.ib(
            default=int(os.getenv('SSH_KEY_SIZE', '4096')))
    ssh_keys_dir = attr.ib(
            default=os.getenv('SSH_KEYS_DIR', '../data/ssh'))

Config = ConfigClass()
