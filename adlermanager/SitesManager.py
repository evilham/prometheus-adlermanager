import attr
from munch                   import Munch
from twisted.python.filepath import FilePath
from twisted.logger          import Logger
from twisted.internet        import reactor, defer, task

from .Config          import Config
from .IncidentManager import IncidentManager, Severity

from .utils  import ensure_dirs, TimestampFile, as_list

class SitesManager(object):
    log = Logger()

    def __init__(self):
        self.sites_dir = FilePath(Config.data_dir).child('sites')
        self.site_managers = {
            site: SiteManager(self.sites_dir.child(site))
            for site in self.load_sites()
        }
        self.tokens = {
            token: manager
            for manager in self.site_managers.values()
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
    monitoring_is_down = attr.ib(default=False)

    _timeout = attr.ib(factory=defer.Deferred)

    def __attrs_post_init__(self):
        self.load_definition()
        self.load_tokens()
        self.last_updated=TimestampFile(self.path.child('last_updated.txt'))
        self.service_managers = [
            ServiceManager(self.path.child(s.name), s)
            for s in self.definition.services
        ]
        # TODO: Get monitoring timeout from config
        #       Default to 5 mins
        self._timeout = task.deferLater(reactor, 5 * 60, self.monitoring_down)

    def monitoring_down(self):
        self.monitoring_is_down = True
        for manager in self.service_managers:
            manager.monitoring_down(self.last_updated.get())

    def load_definition(self):
        with self.path.child('site.yml').open('r') as f:
            self.definition = Munch.fromYAML(f.read())

    def load_tokens(self):
        tokens_file = self.path.child('tokens.txt')
        if tokens_file.exists():
            with open(tokens_file.path, 'r') as f:
                self.tokens = [line.strip() for line in f]
        if not self.tokens:
            log.warn('Site {}: No tokens exist, '
                     'your site will never update'.format(self.definition.title))

    def process_alerts(self, alerts):
        self.last_updated.now()

        # TODO: Get monitoring timeout from config
        #       Default to 5 mins
        self.monitoring_is_down = False
        self._timeout.cancel()
        self._timeout = task.deferLater(reactor, 5 * 60, self.monitoring_down)

        for alert in alerts:
            alert.status = Severity.from_string(alert.labels.get(severity, "OK"))
        # TODO document the heartbeat awfulness somewhere
        # TODO: search for a list-splitting function this way:
        heartbeats = [
            alert
            for alert in alerts
            if alert.labels.get('alertname') == 'EverythingIsFine'
        ]
        alerts = [
            alert
            for alert in alerts
            if alert.labels.get('alertname') != 'EverythingIsFine'
        ]

        for manager in self.service_managers:
            manager.process_heartbeats(heartbeats, self.last_updated.get())
            manager.process_alerts(alerts, self.last_updated.get())

    @property
    def status(self):
        if self.monitoring_is_down:
            return Severity.ERROR
        return max((service.status for service in self.service_managers),
                   default=Severity.OK)

@attr.s
class ServiceManager(object):
    path             = attr.ib()
    definition       = attr.ib()
    current_incident = attr.ib(default=None)
    component_names  = attr.ib(factory=list)

    log = Logger()

    def __attrs_post_init__(self):
        # TODO: Recover status after server restart
        self.component_names = [component.name
                                for component in self.definition.components]

    def monitoring_down(self, timestamp):
        if self.current_incident:
            self.current_incident.monitoring_down(timestamp)

    def process_heartbeats(self, heartbeats, timestamp):
        if self.current_incident:
            self.current_incident.process_heartbeats(heartbeats)

    def process_alerts(self, alerts, timestamp):
        # Filter by service-affecting alerts
        alerts = [alert
                  for alert in alerts
                  if alert.labels.alertname in self.component_names]

        if alerts and not self.current_incident:
            # Something is up, open an incident
            self.current_incident = IncidentManager(self.path.child(timestamp))
            # Notify when incident is considered resolved
            self.current_incident.expired.addCallback(self.resolve_incident)

        if self.current_incident:
            self.current_incident.process_alerts(alerts, timestamp)

    def resolve_incident(self):
        self.current_incident = None

    @property
    def status(self):
        if self.current_incident:
            return max((alert.status for alert in self.current_incident.alerts),
                    default=Severity.OK)
        return Severity.OK

    @property
    def past_incidents(self):
        past = self.path.children().sort()
        if self.current_incident and self.current_incident.path in past:
            past.remove(self.current_incident.path)
        past.reverse()  # Beautiful sleepless code poetry
        # TODO: get limit from config?
        return past[:5]

    @property
    def components(self):
        return [
            {
                "definition": component,
                "status": self.current_incident.component_status(component.name)
                if self.current_incident else Severity.OK
            }
            for component in self.definition.components
        ]
