import attr
import itertools
from munch import Munch
from twisted.python.filepath import FilePath
from twisted.logger import Logger
from twisted.internet import reactor, defer, task

from .Config import Config
from .IncidentManager import IncidentManager, Severity

from .utils import ensure_dirs, TimestampFile, read_timestamp


class SitesManager(object):
    log = Logger()

    def __init__(self):
        self.sites_dir = FilePath(Config.data_dir).child("sites")
        self.site_managers = {
            site: SiteManager(self.sites_dir.child(site)) for site in self.load_sites()
        }
        self.tokens = {
            token: manager
            for manager in self.site_managers.values()
            for token in manager.tokens
        }

    def load_sites(self):
        for site_dir in self.sites_dir.children():
            if not site_dir.isdir():
                continue
            yield site_dir.basename()


def import_alert(alert):
    # Convert date data types
    for att in ["startsAt", "endsAt"]:
        if att in alert:
            try:
                alert[att] = read_timestamp(alert[att])
            except:
                del alert[att]
    # Convert severity (needs date data)
    alert.status = Severity.from_alert(alert)
    return alert


@attr.s
class SiteManager(object):
    path = attr.ib()
    tokens = attr.ib(factory=list)
    log = Logger()
    monitoring_is_down = attr.ib(default=False)

    _timeout = attr.ib(factory=defer.Deferred)
    site_name = attr.ib(default="")
    # TODO: Get monitoring timeout from config
    #       Default to 2 mins
    _timeout_seconds = 2 * 60

    def __attrs_post_init__(self):
        self.load_definition()
        self.load_tokens()
        self.last_updated = TimestampFile(self.path.child("last_updated.txt"))
        self.service_managers = [
            ServiceManager(path=self.path.child(s.label), definition=s)
            for s in self.definition.services
        ]
        self.site_name = self.path.basename()
        self._timeout = task.deferLater(
            reactor, self._timeout_seconds, self.monitoring_down
        )

    def monitoring_down(self):
        self.monitoring_is_down = True
        for manager in self.service_managers:
            manager.monitoring_down(self.last_updated.getStr())

    def load_definition(self):
        with self.path.child("site.yml").open("r") as f:
            self.definition = Munch.fromYAML(f.read())

    def load_tokens(self):
        tokens_file = self.path.child("tokens.txt")
        if tokens_file.exists():
            with open(tokens_file.path, "r") as f:
                self.tokens = [line.strip() for line in f]
        if not self.tokens:
            log.warn(
                "Site {}: No tokens exist, "
                "your site will never update".format(self.definition.title)
            )

    def process_alerts(self, alerts):
        self.last_updated.now()

        self.monitoring_is_down = False
        self._timeout.cancel()
        self._timeout = task.deferLater(
            reactor, self._timeout_seconds, self.monitoring_down
        )

        # Filter alerts for this site
        alerts = [
            import_alert(a)
            for a in alerts
            if a.get("labels", {}).get("adlermanager", "") == self.site_name
        ]

        heartbeats, filtered_alerts = [], []
        for a in alerts:
            (heartbeats if a.labels.get("heartbeat") else filtered_alerts).append(a)

        for manager in self.service_managers:
            manager.process_heartbeats(heartbeats, self.last_updated.getStr())
            manager.process_alerts(filtered_alerts, self.last_updated.getStr())

    @property
    def status(self):
        if self.monitoring_is_down:
            return Severity.ERROR
        return max(
            (service.status for service in self.service_managers), default=Severity.OK
        )


@attr.s
class ServiceManager(object):
    path = attr.ib()
    definition = attr.ib()
    current_incident = attr.ib(default=None)
    component_labels = attr.ib(factory=list)

    log = Logger()

    def __attrs_post_init__(self):
        # TODO: Recover status after server restart
        self.component_labels = [
            component.label for component in self.definition.components
        ]

    def monitoring_down(self, timestamp):
        if self.current_incident:
            self.current_incident.monitoring_down(timestamp)

    def process_heartbeats(self, heartbeats, timestamp):
        if self.current_incident:
            self.current_incident.process_heartbeats(heartbeats, timestamp)

    def process_alerts(self, alerts, timestamp):
        # Filter by service-affecting alerts
        alerts = [
            alert
            for alert in alerts
            if alert.labels.service == self.definition.label
            and alert.labels.component in self.component_labels
        ]

        if alerts and not self.current_incident:
            # Something is up, open an incident
            self.current_incident = IncidentManager(self.path.child(timestamp))
            if not self.path.isdir():
                self.path.createDirectory()
            # Notify when incident is considered resolved
            self.current_incident.expired.addCallback(self.resolve_incident)

        if self.current_incident:
            self.current_incident.process_alerts(alerts, timestamp)

    def resolve_incident(self):
        self.current_incident = None

    @property
    def status(self):
        if self.current_incident:
            # TODO: Consistent naming
            return max(
                (
                    alert.status
                    for alert in self.current_incident.active_alerts.values()
                ),
                default=Severity.OK,
            )
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
            Munch.fromDict(
                {
                    "definition": component,
                    "status": self.current_incident.component_status(component.label)
                    if self.current_incident
                    else Severity.OK,
                }
            )
            for component in self.definition.components
        ]
