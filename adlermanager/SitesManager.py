from typing import Any, Dict, Generator, List, cast

import attr
import yaml
from twisted.internet import defer, reactor, task
from twisted.logger import Logger
from twisted.python.filepath import FilePath

from .Config import Config
from .IncidentManager import IncidentManager
from .model import Alert, Severity
from .utils import TimestampFile, default_errback, noop_deferred


class SitesManager(object):
    log = Logger()

    def __init__(self) -> None:
        self.sites_dir = FilePath(Config.data_dir).child("sites")
        self.site_managers = {
            site: SiteManager(self.sites_dir.child(site)) for site in self.load_sites()
        }
        self.tokens: Dict[str, SiteManager] = {
            token: manager
            for manager in self.site_managers.values()
            for token in manager.tokens
        }

    def load_sites(self) -> Generator[str, None, None]:
        for site_dir in self.sites_dir.children():
            if not site_dir.isdir():
                continue
            yield cast(str, site_dir.basename())


@attr.s
class SiteManager(object):
    path: FilePath = attr.ib()
    tokens: List[str] = attr.ib(factory=list)
    log = Logger()
    monitoring_is_down = attr.ib(default=False)
    definition: Dict[str, Any] = attr.ib(factory=dict)
    title = attr.ib(default="")

    _timeout: defer.Deferred[None] = attr.ib(factory=noop_deferred)
    site_name = attr.ib(default="")
    # TODO: Get monitoring timeout from config
    #       Default to 2 mins
    _timeout_seconds = 2 * 60

    def __attrs_post_init__(self):
        self.load_definition()
        self.title = self.definition["title"]
        self.load_tokens()
        self.last_updated = TimestampFile(self.path.child("last_updated.txt"))
        self.service_managers = [
            ServiceManager(path=self.path.child(s["label"]), definition=s)
            for s in cast(List[Dict[str, Any]], self.definition.get("services", dict()))
        ]
        self.site_name = self.path.basename()
        self._timeout = task.deferLater(
            reactor, self._timeout_seconds, self.monitoring_down  # type: ignore
        ).addErrback(default_errback)

    def monitoring_down(self) -> None:
        self.monitoring_is_down = True
        for manager in self.service_managers:
            manager.monitoring_down(self.last_updated.getStr())

    def load_definition(self):
        with self.path.child("site.yml").open("r") as f:
            self.definition = yaml.safe_load(f)

    def load_tokens(self):
        tokens_file = self.path.child("tokens.txt")
        if tokens_file.exists():
            with open(tokens_file.path, "r") as f:
                self.tokens = [line.strip() for line in f]
        if not self.tokens:
            self.log.warn(
                "Site {}: No tokens exist, "
                "your site will never update".format(self.title)
            )

    def process_alerts(self, raw_alerts: List[Dict[str, Any]]):
        self.last_updated.now()

        self.monitoring_is_down = False
        self._timeout.cancel()
        self._timeout = task.deferLater(
            reactor, self._timeout_seconds, self.monitoring_down  # type: ignore
        ).addErrback(default_errback)

        # Filter alerts for this site
        alerts: List[Alert] = []
        for ra in raw_alerts:
            if (
                ra.get("labels", {}).get("adlermanager", "") == self.site_name
                and ra.get("labels", {}).get("component", "")
                and ra.get("labels", {}).get("service", "")
            ):
                alerts.append(Alert.import_alert(ra))

        heartbeats: List[Alert] = []
        filtered_alerts: List[Alert] = []
        for a in alerts:
            (heartbeats if a.labels.get("heartbeat") else filtered_alerts).append(a)

        timestamp = self.last_updated.getStr()
        for manager in self.service_managers:
            manager.process_heartbeats(heartbeats, timestamp)
            manager.process_alerts(filtered_alerts, timestamp)

    @property
    def status(self):
        if self.monitoring_is_down:
            return Severity.ERROR
        return max(
            (service.status for service in self.service_managers), default=Severity.OK
        )


@attr.s
class ServiceManager(object):
    path: FilePath = attr.ib()
    definition: Dict[str, Any] = attr.ib()
    current_incident = attr.ib(default=None)
    component_labels: List[str] = attr.ib(factory=list)
    label = attr.ib(default="")

    log = Logger()

    def __attrs_post_init__(self):
        self.label = self.definition["label"]
        # TODO: Recover status after server restart
        self.component_labels = [
            component["label"]
            for component in cast(
                List[Dict[str, Any]], self.definition.get("components", [])
            )
        ]

    def monitoring_down(self, timestamp: str) -> None:
        if self.current_incident:
            self.current_incident.monitoring_down(timestamp)

    def process_heartbeats(self, heartbeats: List[Alert], timestamp: str):
        if self.current_incident:
            self.current_incident.process_heartbeats(heartbeats, timestamp)

    def process_alerts(self, alerts: List[Alert], timestamp: str):
        # Filter by service-affecting alerts
        alerts = [
            alert
            for alert in alerts
            if alert.labels.get("service") == self.label
            and alert.labels.get("component") in self.component_labels
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

    def resolve_incident(self) -> None:
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

    # @property
    # def past_incidents(self):
    #     past = self.path.children().sort()
    #     if self.current_incident and self.current_incident.path in past:
    #         past.remove(self.current_incident.path)
    #     past.reverse()  # Beautiful sleepless code poetry
    #     # TODO: get limit from config?
    #     return past[:5]

    @property
    def components(self) -> List[Dict[str, Any]]:
        return [
            {
                "definition": component,
                "status": self.current_incident.component_status(component["label"])
                if self.current_incident
                else Severity.OK,
            }
            for component in self.definition.get("components", [])
        ]
