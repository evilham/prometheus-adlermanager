import attr
from munch                   import Munch
from twisted.python.filepath import FilePath
from twisted.logger          import Logger

from .Config          import Config
from .IncidentManager import IncidentManager, Severity

from .utils  import ensure_dirs, TimestampFile, as_list

class SitesManager(object):
    log = Logger()

    def __init__(self):
        self.sites_dir = FilePath(Config.data_dir).child('sites')
        self.site_managers = [
            SiteManager(self.sites_dir.child(site))
            for site in self.load_sites()
        ]
        self.tokens = {
            token: manager
            for manager in self.site_managers
            for token in manager.tokens
        }

    @as_list
    def load_sites(self):
        for site_dir in self.sites_dir.children():
            if not site_dir.isdir(): continue
            yield site_dir.basename()


@attr.s
class SiteManager(object):
    path   = attr.ib()
    tokens = attr.ib(factory=list)
    log    = Logger()

    def __attrs_post_init__(self):
        self.load_definition()
        self.load_tokens()
        self.last_updated=TimestampFile(self.path.child('last_updated.txt'))
        self.service_managers = [
            ServiceManager(self.path.child(s.name), s)
            for s in self.definition.services
        ]

    def load_definition(self):
        with self.path.child('site.yml').open('r') as f:
            self.definition = Munch.fromYAML(f.read())

    def load_tokens(self):
        tokens_file = self.path.child('tokens.txt')
        if tokens_file.exists():
            with tokens_file.open('r') as f:
                self.tokens = [line.strip() for line in f]
        if not self.tokens:
            log.warn('Site {}: No tokens exist, '
                     'your site will never update'.format(self.definition.title))

    def process_alerts(self, alerts):
        self.last_updated.now()
        for service, manager in self.definition.services.items():
            manager.process_alerts(alerts, self.last_updated.get())

    @property
    def status(self):
        return max((service.status for service in self.service_managers), default=Severity.OK)

@attr.s
class ServiceManager(object):
    path             = attr.ib()
    definition       = attr.ib()
    current_incident = attr.ib(default=None)
    past_incidents   = attr.ib(factory=list)
    log = Logger()

    def process_alerts(self, alerts, timestamp):
        for alert in alerts:
            # TODO how exactly do alerts look?
            if alert.labels.component in self.definition.components:
                self.process_alert(alert, timestamp)

    def process_alert(self, alert, timestamp):
        # TODO document the heartbeat awfulness somewhere
        if not self.current_incident and not alert._is_heartbeat:
            # Open an incident only if we get a non-heartbeat alert.
            self.current_incident = IncidentManager(self.path.child(timestamp), timestamp)
            self.current_incident.expired.addCallback(self.resolve_incident)

        if self.current_incident:
            self.log.info("Alert: {alert}", alert=alert)
            self.current_incident.process_alert(alert, timestamp)

    def resolve_incident(self):
        # TODO: Further clean-up
        self.current_incident = None

    @property
    def status(self):
        # TODO
        return max((alert.status for alert in self.current_incident.alerts), default=Severity.OK)
