#!/usr/bin/env python3

# Run with twistd -ny app.py

from twisted.application import service, strports
from twisted.web import server
from twisted.python.filepath import FilePath

from adlermanager import Config, SitesManager
from adlermanager import web_root

if not FilePath(Config.data_dir).isdir():
    FilePath(Config.data_dir).createDirectory()

application = service.Application("AdlerManager")
serv_collection = service.IServiceCollection(application)

# TokenResource
sites_manager = SitesManager()

resource = web_root(sites_manager)
site = server.Site(resource)
i = strports.service(Config.web_endpoint, site)  # type: ignore
i.setServiceParent(serv_collection)  # type: ignore

if Config.ssh_enabled:
    # Set up SSH config service
    from adlermanager.AdlerManagerSSHProtocol import AdlerManagerSSHProtocol
    from adlermanager.conch_helpers import conch_helper

    # TODO: Make this more decent
    AdlerManagerSSHProtocol.sites_manager = sites_manager
    i = conch_helper(
        Config.ssh_endpoint,
        proto=AdlerManagerSSHProtocol,
        keyDir=Config.ssh_keys_dir,
        keySize=Config.ssh_key_size,
    )
    i.setServiceParent(serv_collection)  # type: ignore
