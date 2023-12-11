import functools
import json
from typing import TYPE_CHECKING, Any, Dict, Optional

import attr
import yaml

from .conch_helpers import SSHSimpleAvatar, SSHSimpleProtocol
from .model import SiteConfig

if TYPE_CHECKING:
    from adlermanager.SitesManager import SiteManager, SitesManager


class AdlerManagerSSHProtocol(SSHSimpleProtocol):
    sites_manager: "SitesManager"

    def __init__(self, user: SSHSimpleAvatar) -> None:
        """
        Create an instance of AdlerManagerSSHProtocol.
        """
        SSHSimpleProtocol.__init__(self, user)

        # TODO: Do stuff like getting user sites, showing alert warnings, etc.

    def do_list_sites(self) -> None:
        """
        List all sites to which you have access
        """
        o: Dict[str, Any] = dict()
        for k, sm in self.sites_manager.get_user_sites(self.user.username).items():
            o[k] = {
                "config": attr.asdict(sm.site_config),
                "status": {"value": sm.status.value, "message": str(sm.status)},
                "title": sm.title,
            }
        self.terminal_write(yaml.safe_dump(o, allow_unicode=True))
        self.terminal.nextLine()

    def _get_user_site_manager(self, site: bytes) -> Optional["SiteManager"]:
        try:
            s = site.decode("utf-8")
        except Exception:
            self.terminal_write("Error: Received invalid site name")
            self.terminal.nextLine()
            return None
        if s not in self.sites_manager.get_user_sites(self.user.username):
            self.terminal_write("Warning: requested unknown or unaccessible site")
            self.terminal.nextLine()
            return None
        return self.sites_manager.get_user_sites(self.user.username)[s]

    def do_get_site_config(self, site: bytes) -> None:
        """
        Get a site's configuration. Usage: get_site_config status.example.org
        """
        sm = self._get_user_site_manager(site)
        if sm is not None:
            self.terminal_write(sm.site_config.to_YAML())

    async def do_set_site_config(self, site: bytes) -> None:
        """
        Set a site's configuration.

        The second argument may be ommitted if running in a non-interactive
        fashion, in which case stdin will be used.

        Usage: set_site_config status.example.org \\
            [{"force_state": True, "message": "Hello world!\\n\\nThis is an example"}]
        """
        if self.interactive:
            self.terminal_write("Finish your YAML input with a line like this:")
            self.terminal.nextLine()
            self.terminal_write("---")
            self.terminal.nextLine()
        sm = self._get_user_site_manager(site)
        if sm is not None:
            data = await self.get_user_input(eom=b"---")
            if data is None or data == b"":
                raise SyntaxError("No data was received")
            try:
                sc = SiteConfig.from_YAML(data)
            except Exception:
                raise SyntaxError("SiteConfig could not be created from data")
            if self.interactive:
                self.terminal_write(sc.to_YAML())
                self.terminal_write("Does this look fine? [Y/n] ")
                ans = await self.get_user_input()
                if ans.decode("utf-8").strip().upper() not in ["Y", ""]:
                    self.terminal_write("Aborting")
                    self.terminal.nextLine()
                    return
            # Actually do something
            sm.site_config = sc
            sm.config_file.setContent(sc.to_YAML().encode("utf-8"))
            sm.config_file.chmod(0o640)
            if self.interactive:
                self.terminal_write("Persisted SiteConfiguration")
                self.terminal.nextLine()

    def do_tmp_dump_state(self) -> None:
        """
        This command is temporary and just dumps all known state.
        """
        for k, sm in self.sites_manager.get_user_sites(self.user.username).items():
            self.terminal_write(f"\n#\n# {k}\n#\n")
            for _, srv in sm.service_managers.items():
                self.terminal_write(f"## {srv.label}\n")
                self.terminal_write(json.dumps(srv.components))
                self.terminal.nextLine()
        self.terminal.nextLine()

    @functools.lru_cache()  # we don't need to re-read every time
    def motd(self) -> str:
        # TODO: Use data location?
        return open("motd.txt").read()
