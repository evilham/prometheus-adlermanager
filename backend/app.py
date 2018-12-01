#!/usr/bin/env python3

# Run with twistd -ny app.py

from twisted.internet import reactor, endpoints
from twisted.application import service, strports
from twisted.application.internet import ClientService
from twisted.web import server

# Add current dir to path. Ugly but it works.
import sys
import os
sys.path += [ os.path.dirname(os.path.realpath(__file__)) ]

from adlermanager import Config, SitesManager
from adlermanager import AdlerManagerTokenResource
from adlermanager import conch_helper, AdlerManagerSSHProtocol


application = service.Application('AdlerManager')
serv_collection = service.IServiceCollection(application)

# TokenResource
sites_manager = SitesManager()

resource = AdlerManagerTokenResource(site_manager)
site = server.Site(resource)
i = strports.service(Config.web_endpoint, site)
i.setServiceParent(serv_collection)

# Set up SSH config service

# TODO: Make this more decent
AdlerManagerSSHProtocol.site_manager = site_manager

i = conch_helper(
    Config.ssh_endpoint,
    proto=AdlerManagerSSHProtocol,
    keyDir=Config.ssh_keys_dir,
    keySize=Config.ssh_key_size)
i.setServiceParent(serv_collection)
