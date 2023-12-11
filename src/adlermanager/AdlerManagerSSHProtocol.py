import functools
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import attr
import yaml
from twisted.logger import Logger
from twisted.python.filepath import FilePath

from .conch_helpers import SSHSimpleAvatar, SSHSimpleProtocol
from .model import SiteConfig

if TYPE_CHECKING:
    from adlermanager.SitesManager import SiteManager, SitesManager

log = Logger()


class AdlerManagerSSHProtocol(SSHSimpleProtocol):
    sites_manager: "SitesManager"

    def __init__(self, user: SSHSimpleAvatar) -> None:
        """
        Create an instance of AdlerManagerSSHProtocol.
        """
        SSHSimpleProtocol.__init__(self, user)
        log.info("SSH login for {user}", user=user.username)

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
            log.info(
                "User {user} changed {site} config", user=self.user.username, site=site
            )
            if self.interactive:
                self.terminal_write("Persisted SiteConfiguration")
                self.terminal.nextLine()

    @functools.lru_cache()  # we don't need to re-read every time
    def motd(self) -> Union[str, bytes]:
        custom_motd = FilePath(self.sites_manager.global_config.data_dir).child(
            "motd.txt"
        )
        if custom_motd.isfile():
            return custom_motd.getContent()
        # Default motd
        return FilePath(__file__).parent().child("motd.txt").getContent()
