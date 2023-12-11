from typing import Any, Dict, Generator, List, Optional, cast

import attr
import yaml
from twisted.internet import defer, reactor, task
from twisted.logger import Logger
from twisted.python.filepath import FilePath

from .Config import ConfigClass
from .IncidentManager import IncidentManager
from .model import Alert, Severity, SiteConfig
from .utils import TimestampFile, default_errback, noop_deferred


@attr.s
class SitesManager(object):
    global_config: ConfigClass = attr.ib()
    site_managers: Dict[str, "SiteManager"] = attr.ib(factory=dict)
    tokens: Dict[str, "SiteManager"] = attr.ib(factory=dict)
    log: Logger = attr.ib(factory=Logger)

    def __attrs_post_init__(self) -> None:
        def startup_message() -> None:
            self.log.info(
                f"Starting server with this configuration:\n{self.global_config}",
                system=SitesManager.__name__,
            )

        # Inform people of current configuration when reactor starts
        _ = task.deferLater(reactor, 0, startup_message).addErrback(  # type: ignore
            default_errback
        )
        # Load data
        self.reload()

    def reload(self) -> "SitesManager":
        # Read sites
        read_sites = {
            site: self.site_managers[site].reload()
            if site in self.site_managers
            else SiteManager(
                global_config=self.global_config, path=self.sites_dir.child(site)
            )
            for site in self.load_sites()
        }
        # Remove deleted sites
        for deleted_site in set(self.site_managers.keys()).difference(
            read_sites.keys()
        ):
            del self.site_managers[deleted_site]
        # Apply update / add new sites
        self.site_managers.update(read_sites)
        # Re-read all sites
        self.tokens.clear()
        self.tokens.update(
            {
                token: manager
                for manager in self.site_managers.values()
                for token in manager.tokens
            }
        )
        return self

    @property
    def sites_dir(self) -> FilePath:
        return FilePath(self.global_config.data_dir).child("sites")

    def load_sites(self) -> Generator[str, None, None]:
        for site_dir in self.sites_dir.children():
            if not site_dir.isdir():
                continue
            yield cast(str, site_dir.basename())  # type: ignore

    def get_user_sites(self, username: bytes) -> Dict[str, "SiteManager"]:
        o: Dict[str, SiteManager] = dict()
        try:
            u = username.decode("utf-8")
        except Exception:
            return o
        for k, sm in self.site_managers.items():
            if u in sm.ssh_users:
                o[k] = sm
        return o


@attr.s
class SiteManager(object):
    global_config: ConfigClass = attr.ib()
    path: FilePath = attr.ib()
    tokens: List[str] = attr.ib(factory=list)
    ssh_users: List[str] = attr.ib(factory=list)
    monitoring_is_down: bool = attr.ib(default=False)
    definition: Dict[str, Any] = attr.ib(factory=dict)
    title: str = attr.ib(default="")
    site_config: SiteConfig = attr.ib(factory=SiteConfig)
    service_managers: Dict[str, "ServiceManager"] = attr.ib(factory=dict)

    _timeout: defer.Deferred[None] = attr.ib(factory=noop_deferred)
    site_name: str = attr.ib(default="")

    @property
    def monitoring_down_seconds(self) -> float:
        return self.global_config.monitoring_down_minutes.total_seconds()

    log: Logger = attr.ib(factory=Logger)

    def __attrs_post_init__(self) -> None:
        self.reload()

    def reload(self) -> "SiteManager":
        self.load_definition()
        self.title = self.definition["title"]
        self.load_tokens()
        self.site_config = self.load_config()
        self.site_name = self.path.basename()
        self.last_updated = TimestampFile(self.path.child("last_updated.txt"))
        # Read services
        read_services: Dict[str, ServiceManager] = {
            s["label"]: self.service_managers[s["label"]].reload(s)
            if s["label"] in self.service_managers
            else ServiceManager(
                global_config=self.global_config,
                path=self.path.child(s["label"]),
                definition=s,
            )
            for s in cast(List[Dict[str, Any]], self.definition.get("services", dict()))
        }
        # Remove deleted servicse
        for deleted_service in set(self.service_managers.keys()).difference(
            read_services.keys()
        ):
            del self.service_managers[deleted_service]
        # Apply update / add new sites
        self.service_managers.update(read_services)

        # Add/reset monitoring timeout
        self._timeout.cancel()
        self._timeout = task.deferLater(
            reactor, self.monitoring_down_seconds, self.monitoring_down  # type: ignore
        ).addErrback(default_errback)
        return self

    def monitoring_down(self) -> None:
        self.monitoring_is_down = True
        for _, manager in self.service_managers.items():
            manager.monitoring_down(self.last_updated.getStr())

    def load_definition(self) -> None:
        with self.path.child("site.yml").open("r") as f:
            self.definition = yaml.safe_load(f)
            self.ssh_users.clear()
            self.ssh_users.extend((u for u in self.definition.get("ssh_users", [])))

    def load_tokens(self) -> None:
        tokens_file = self.path.child("tokens.txt")
        if tokens_file.exists():
            with open(tokens_file.path, "r") as f:
                self.tokens = [line.strip() for line in f]
        if not self.tokens:
            self.log.warn(
                "Site {}: No tokens exist, "
                "your site will never update".format(self.title)
            )

    @property
    def config_file(self) -> FilePath:
        return self.path.child("config.yaml")

    def load_config(self) -> SiteConfig:
        try:
            return SiteConfig.from_YAML(self.config_file.getContent())
        except Exception:
            return SiteConfig()

    def process_alerts(self, raw_alerts: List[Dict[str, Any]]) -> None:
        self.last_updated.now()

        self.monitoring_is_down = False
        self._timeout.cancel()
        self._timeout = task.deferLater(
            reactor, self.monitoring_down_seconds, self.monitoring_down  # type: ignore
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
        for _, manager in self.service_managers.items():
            manager.process_heartbeats(heartbeats, timestamp)
            manager.process_alerts(filtered_alerts, timestamp)

    @property
    def status(self) -> Severity:
        if self.monitoring_is_down:
            return Severity.ERROR
        return max(
            (service.status for _, service in self.service_managers.items()),
            default=Severity.OK,
        )


@attr.s
class ServiceManager(object):
    global_config: ConfigClass = attr.ib()
    path: FilePath = attr.ib()
    definition: Dict[str, Any] = attr.ib()
    current_incident: Optional[IncidentManager] = attr.ib(default=None)
    component_labels: List[str] = attr.ib(factory=list)
    label: str = attr.ib(default="")

    def __attrs_post_init__(self) -> None:
        self.reload()

    def reload(self, definition: Dict[str, Any] = {}) -> "ServiceManager":
        if definition:
            # This should only happen when reloading
            self.definition.clear()
            self.definition.update(definition)
        self.label = self.definition["label"]
        self.component_labels.clear()
        self.component_labels.extend(
            [
                component["label"]
                for component in cast(
                    List[Dict[str, Any]], self.definition.get("components", [])
                )
            ]
        )
        return self

    def monitoring_down(self, timestamp: str) -> None:
        if self.current_incident:
            self.current_incident.monitoring_down(timestamp)

    def process_heartbeats(self, heartbeats: List[Alert], timestamp: str) -> None:
        if self.current_incident:
            self.current_incident.process_heartbeats(heartbeats, timestamp)

    def process_alerts(self, alerts: List[Alert], timestamp: str) -> None:
        # Filter by service-affecting alerts
        alerts = [
            alert
            for alert in alerts
            if alert.labels.get("service") == self.label
            and alert.labels.get("component") in self.component_labels
        ]

        if alerts and not self.current_incident:
            # Something is up, open an incident
            self.current_incident = IncidentManager(
                global_config=self.global_config,
                path=self.path,
            )
            # Notify when incident is considered resolved
            _ = self.current_incident.expired.addCallback(self.resolve_incident)

        if self.current_incident:
            self.current_incident.process_alerts(alerts, timestamp)

    def resolve_incident(self, _: Any) -> None:
        self.current_incident = None

    @property
    def status(self) -> Severity:
        if self.current_incident:
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
