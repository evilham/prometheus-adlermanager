import attr
import json
import rfc3339
import copy
from datetime import datetime
from enum import IntEnum
from munch import Munch
from twisted.python.filepath import FilePath
from twisted.internet import reactor, defer, task

from .Config import Config
from .utils import ensure_dirs, TimestampFile, current_timestamp

FILENAME_TIME_FORMAT = "%Y-%m-%d-%H%MZ"


class Severity(IntEnum):
    OK = 0
    WARNING = 1
    ERROR = 2

    @classmethod
    def from_string(cls, s):
        # TODO: Do something sensitive with other priorities
        #       At least document them somewhere :-D
        labels = {
            "ok": cls.OK,
            "warning": cls.WARNING,
            "error": cls.ERROR,
        }
        return labels[s.lower()]

    @property
    def css(self):
        classes = {self.OK: "success", self.WARNING: "warning", self.ERROR: "danger"}
        return classes[self]

    def __str__(self):
        return self.css


@attr.s
class IncidentManager(object):
    path = attr.ib()

    last_alert = attr.ib(default="")
    active_alerts = attr.ib(factory=dict)
    expired = attr.ib(factory=defer.Deferred)
    _timeout = attr.ib(factory=defer.Deferred)
    _alert_timeouts = attr.ib(factory=dict)  # alert name => timeout

    _monitoring_down = attr.ib(default=False)

    _logs = attr.ib(factory=list)
    # TODO: Get IncidentClosing timeout from settings?
    #       Defaulting to 30m
    _monitoring_grace_period = attr.ib(default=60 * 30)
    #       Defaulting to 5m
    _alertExpireTime = attr.ib(default=5 * 60)

    def process_heartbeats(self, heartbeats, timestamp):
        if heartbeats:
            self.last_updated = timestamp
            if self._monitoring_down:
                self._monitoring_down = False
                # Monitoring is back up, re-activate timeout
                self._timeout = task.deferLater(
                    reactor, self._monitoring_grace_period, self._expire
                )
                self.log_event("[Meta]MonitoringUp", timestamp)

    def process_alerts(self, alerts, timestamp):
        if alerts:
            self._timeout.cancel()
            self._timeout = task.deferLater(
                reactor, self._monitoring_grace_period, self._expire
            )
            self.last_alert = timestamp

        new_alerts = dict()

        for alert in alerts:
            alertname = alert.labels.alertname
            if alertname in self._alert_timeouts:
                self._alert_timeouts[alertname].cancel()
            else:
                new_alerts[alertname] = alert
            self.active_alerts[alertname] = alert
            self._alert_timeouts[alertname] = task.deferLater(
                reactor, self._alertExpireTime, self._expire_alert, alertname
            )

        if new_alerts:
            self.log_event("New", timestamp, alerts=list(new_alerts.values()))

    def _expire(self):
        if not self._monitoring_down:
            self.expired.callback(self)

    def _expire_alert(self, alertname):
        self.log_event(
            "Resolved", current_timestamp(), alert=self.active_alerts[alertname]
        )
        del self.active_alerts[alertname]

    def monitoring_down(self, timestamp):
        self._monitoring_down = True
        self.log_event("[Meta]MonitoringDown", timestamp)

    def log_event(self, message, timestamp, alerts=[], alert=None):
        if alert is not None:
            alerts.append(alert)
        obj = {"message": message, "timestamp": timestamp}
        if alerts:
            alerts = copy.deepcopy(alerts)
            for alert in alerts:
                alert.status = alert.status.css
            obj["alerts"] = alerts
        self._logs.append(obj)
        # Persist messages
        with self.path.open("w") as f:
            m = Munch.fromDict({"log": self._logs, "timestamp": timestamp})
            f.write(m.toYAML().encode("utf-8"))

    def component_status(self, component):
        return max(
            (
                alert.status
                for alert in self.active_alerts.values()
                if alert.labels.alertname == component
            ),
            default=Severity.OK,
        )
