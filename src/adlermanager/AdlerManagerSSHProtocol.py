import functools
import json
from typing import TYPE_CHECKING, Any, Dict

import yaml

from .conch_helpers import SSHSimpleAvatar, SSHSimpleProtocol

if TYPE_CHECKING:
    from adlermanager.SitesManager import SitesManager


class AdlerManagerSSHProtocol(SSHSimpleProtocol):
    sites_manager: "SitesManager"

    def __init__(self, user: SSHSimpleAvatar, interactive: bool = True) -> None:
        """
        Create an instance of AdlerManagerSSHProtocol.
        """
        SSHSimpleProtocol.__init__(self, user, interactive=interactive)

        # TODO: Do stuff like getting user sites, showing alert warnings, etc.

    def do_list_sites(self) -> None:
        """
        List all sites to which you have access
        """
        o: Dict[str, Any] = dict()
        for k, sm in self.sites_manager.get_user_sites(self.user.username).items():
            o[k] = {
                "title": sm.title,
                "status": {"value": sm.status.value, "message": str(sm.status)},
            }
        self.terminal_write(yaml.safe_dump(o, allow_unicode=True))
        self.terminal.nextLine()

    def do_tmp_dump_state(self) -> None:
        """
        This command is temporary and just dumps all known state.
        """
        for k, sm in self.sites_manager.get_user_sites(self.user.username).items():
            self.terminal_write(f"\n#\n# {k}\n#\n")
            for srv in sm.service_managers:
                self.terminal_write(f"## {srv.label}\n")
                self.terminal_write(json.dumps(srv.components))
                self.terminal.nextLine()
        self.terminal.nextLine()

    @functools.lru_cache()  # we don't need to re-read every time
    def motd(self) -> str:
        # TODO: Use data location?
        return open("motd.txt").read()
