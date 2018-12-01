import attr
import rfc3339
from datetime import datetime, timezone
from munch    import Munch

from .Config          import Config
from .IncidentManager import IncidentManager

from twisted.python.filepath import FilePath

class SitesManager(object):
    def __init__(self):
        self.sites_dir = FilePath(Config.data_dir).child('sites')
        self.sites, self.tokens = self.load_sites_data()
        self.incident_managers = {
            site: IncidentManager(self.sites_dir.child(site).child('incidents'))
            for site in self.sites
        }

    def get_site(self, site):
        return Munch(definition=self.sites[site],
                     incident_manager=self.incident_managers[site],
                     last_updated=self.get_last_updated(site))

    def load_sites_data(self):
        sites  = {}
        tokens = {}
        for site_dir in self.sites_dir.children():
            if not site_dir.isdir(): continue
            site = site_dir.basename()
            with site_dir.child('site.yml').open('r') as f:
                sites[site] = Munch.fromYAML(f.read())
            # TODO this only reads the token on startup, fix it
            try:
                with site_dir.child('tokens.txt').open('r') as f:
                    for line in f:
                        tokens[line.strip()] = site
            except FileNotFoundError:
                pass  # no tokens, whatever
        return sites, tokens

    def update_site(self, site, alert_data):
        now = date.now(timezone.utc)
        self.set_last_updated(self, site, now)
        for alert in alert_data:
            # TODO document the heartbeat awfulness somewhere
            if False: continue  # ignore the heartbeat TODO
            self.incident_managers[site].save_alert(alert, now)

    def _last_updated_file(self, site):
        return self.sites_dir.child(site).child('last_updated.txt')

    def set_last_updated(self, site, now):
        with self._last_updated_file(site).open('w') as f:
            f.write(rfc3339.format(now))

    def get_last_updated(self, site):
        try:
            with self._last_updated_file(site).open('r') as f:
                return date.fromisoformat(f.read())
        except FileNotFoundError:
            return None
