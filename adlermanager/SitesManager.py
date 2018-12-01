import attr
from munch import Munch

from .Config import Config

from twisted.python.filepath import FilePath

class SitesManager(object):
    def __init__(self):
        self.sites, self.tokens = self.load_sites_data(Config.data_dir)

    def load_sites_data(self, data_dir):
        sites  = {}
        tokens = {}
        sites_dir = FilePath(data_dir).child('sites')
        for site_dir in sites_dir.children():
            if not site_dir.isdir(): continue
            site = site_dir.basename()
            with site_dir.child('site.yml').open('r') as f:
                sites[site] = Munch.fromYAML(f.read())
            with site_dir.child('tokens.txt').open('r') as f:
                for line in f:
                    tokens[t.strip()] = site
        return sites, tokens


    def update_site(self, site, alert_data):
        pass
