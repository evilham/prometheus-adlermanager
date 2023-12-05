import functools
import json
from typing import TYPE_CHECKING

from .conch_helpers import SSHSimpleAvatar, SSHSimpleProtocol

if TYPE_CHECKING:
    from adlermanager.SitesManager import SitesManager


class AdlerManagerSSHProtocol(SSHSimpleProtocol):
    sites_manager: "SitesManager"

    def __init__(self, user: SSHSimpleAvatar):
        """
        Create an instance of AdlerManagerSSHProtocol.
        """
        SSHSimpleProtocol.__init__(self, user)

        # TODO: Do stuff like getting user sites, showing alert warnings, etc.

    def do_tmp_dump_state(self):
        """
        This command is temporary and just dumps all known state.
        """
        for k, sm in self.sites_manager.site_managers.items():
            self.terminal_write(f"\n#\n# {k}\n#\n")
            for srv in sm.service_managers:
                self.terminal_write(f"## {srv.label}\n")
                self.terminal_write(json.dumps(srv.components))
                self.terminal.nextLine()
        self.terminal.nextLine()

    @functools.lru_cache()  # we don't need to re-read every time
    def motd(self):
        # TODO: Use data location?
        return open("motd.txt").read()
