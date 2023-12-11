from typing import Dict, Iterable, List, Optional

import attr
from twisted.internet import defer, reactor, task
from twisted.python.filepath import FilePath

from .Config import ConfigClass
from .model import Alert, Severity
from .utils import current_timestamp, default_errback, noop_deferred

FILENAME_TIME_FORMAT = "%Y-%m-%d-%H%MZ"


@attr.s
class IncidentManager(object):
    global_config: ConfigClass = attr.ib()
    path: FilePath = attr.ib()
    timestamp: str = attr.ib(default="")

    last_alert: str = attr.ib(default="")
    active_alerts: Dict[str, Alert] = attr.ib(factory=dict)
    expired: defer.Deferred[None] = attr.ib(factory=noop_deferred)
    _timeout: defer.Deferred[None] = attr.ib(factory=noop_deferred)
    """Incident timeout"""
    _alert_timeouts: Dict[str, defer.Deferred[None]] = attr.ib(factory=dict)
    """alert_label -> timeout"""

    _monitoring_down: bool = attr.ib(default=False)

    @property
    def incident_grouping_seconds(self) -> float:
        return self.global_config.group_incidents_minutes.total_seconds()

    @property
    def alert_resolve_seconds(self) -> float:
        return self.global_config.alert_resolve_minutes.total_seconds()

    def __attrs_post_init__(self) -> None:
        if not self.path.isdir():
            self.path.createDirectory()

        timestamp_file = self.path.child("timestamp")

        if not self.timestamp:
            if timestamp_file.isfile():
                # The file exists already, read it
                self.timestamp = timestamp_file.getContent().decode("utf-8")
            else:
                # Get timestamp implicitly from path, this is likely a new incident
                #
                # We don't always rely on this, to allow for incident
                # re-naming later on.
                self.timestamp = self.path.basename()

        if not timestamp_file.isfile():
            # Persist the timestamp file if necessary
            timestamp_file.setContent(self.timestamp.encode("utf-8"))
            timestamp_file.chmod(0o644)

    def process_heartbeats(self, heartbeats: Iterable[Alert], timestamp: str) -> None:
        if heartbeats:
            self.last_updated = timestamp
            if self._monitoring_down:
                self._monitoring_down = False
                # Monitoring is back up, re-activate timeout
                self._timeout = task.deferLater(
                    reactor,  # type: ignore
                    self.incident_grouping_seconds,
                    self._expire,
                )
                self.log_event("[Meta]MonitoringUp", timestamp)

    def process_alerts(self, alerts: Iterable[Alert], timestamp: str) -> None:
        if alerts:
            self._timeout.cancel()
            self._timeout = task.deferLater(
                reactor, self.incident_grouping_seconds, self._expire  # type: ignore
            ).addErrback(default_errback)
            self.last_alert = timestamp

        new_alerts: Dict[str, Alert] = dict()

        for alert in alerts:
            alert_label = alert.labels["component"]
            if alert_label in self._alert_timeouts:
                self._alert_timeouts[alert_label].cancel()
            else:
                new_alerts[alert_label] = alert
            # Use highest known severity for a given incident
            # We also allow Resolved alert notifications
            if (
                alert.status == Severity.OK
                or alert.status >= self.active_alerts.get(alert_label, alert).status
            ):
                self.active_alerts[alert_label] = alert
            self._alert_timeouts[alert_label] = task.deferLater(
                reactor,  # type: ignore
                self.alert_resolve_seconds,
                self._expire_alert,
                alert_label,
            ).addErrback(default_errback)

        if new_alerts:
            self.log_event("New", timestamp, alerts=list(new_alerts.values()))

    def _expire(self) -> None:
        if not self._monitoring_down:
            self.expired.callback(self)  # type: ignore  # twisted bug

    def _expire_alert(self, alert_label: str) -> None:
        self.log_event(
            "Resolved", current_timestamp(), alert=self.active_alerts[alert_label]
        )
        del self.active_alerts[alert_label]

    def monitoring_down(self, timestamp: str) -> None:
        self._monitoring_down = True
        self.log_event("[Meta]MonitoringDown", timestamp)

    def log_event(
        self,
        message: str,
        timestamp: str,
        alerts: List[Alert] = [],
        alert: Optional[Alert] = None,
    ) -> None:
        # TODO: we probably actually want something like this
        pass

    # def log_event(
    #     self,
    #     message: str,
    #     timestamp: str,
    #     alerts: List[Alert] = [],
    #     alert: Optional[Alert] = None,
    # ):
    #     if alert is not None:
    #         alerts.append(alert)
    #     obj = {"message": message, "timestamp": timestamp}
    #     if alerts:
    #         alerts = copy.deepcopy(alerts)
    #         for a in alerts:
    #             a.status = a.status.css
    #         obj["alerts"] = alerts
    #     # self._logs.append(obj)
    #     # Persist messages
    #     with self.path.open("w") as f:
    #         m = Munch.fromDict({"log": self._logs, "timestamp": timestamp})
    #         f.write(m.toYAML().encode("utf-8"))

    def component_status(self, component_label: str) -> Severity:
        return max(
            (
                alert.status
                for alert in self.active_alerts.values()
                if alert.labels["component"] == component_label
            ),
            default=Severity.OK,
        )
