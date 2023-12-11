#!/usr/bin/env python3
"""
Run in foreground using:
- a generic service manager: python -m adlermanager
- twistd: twistd -ny src/adlermanager/__main__.py
"""

from typing import Iterable, cast

from twisted.application import service, strports
from twisted.python.filepath import FilePath
from twisted.web import server

from adlermanager import Config, SitesManager, web_root

if not FilePath(Config.data_dir).isdir():
    FilePath(Config.data_dir).createDirectory()

application = service.Application("AdlerManager")
serv_collection = service.IServiceCollection(application)

# TokenResource
sites_manager = SitesManager(global_config=Config)

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


def run():
    import sys

    from twisted import logger

    # Setup global logging to stdout
    logger.globalLogPublisher.addObserver(
        cast(logger.ILogObserver, logger.textFileLogObserver(sys.stdout))
    )

    # Run without twistd as documented upstream:
    # https://docs.twisted.org/en/stable/core/howto/basics.html#twistd
    from twisted.internet import reactor as _reactor  # type: ignore
    from twisted.internet.base import ReactorBase

    reactor = cast(ReactorBase, _reactor)
    for srv in cast(Iterable[service.IService], serv_collection):
        srv.startService()
        reactor.addSystemEventTrigger("before", "shutdown", srv.stopService)

    # Finally, start the reactor
    reactor.run()


if __name__ == "__main__":
    run()
