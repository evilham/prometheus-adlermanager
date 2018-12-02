import attr
import json
import rfc3339
import copy
from datetime                import datetime
from enum                    import IntEnum
from munch                   import Munch
from twisted.python.filepath import FilePath
from twisted.internet        import reactor, defer, task

from .Config import Config
from .utils  import ensure_dirs, TimestampFile, current_timestamp

FILENAME_TIME_FORMAT = '%Y-%m-%d-%H%MZ'


class Severity(IntEnum):
    OK      = 0
    WARNING = 1
    ERROR   = 2

    @classmethod
    def from_string(cls, s):
        labels = {
            "ok":      cls.OK,
            "warning": cls.WARNING,
            "error":   cls.ERROR,
        }
        return labels[s.lower()]

    @property
    def css(self):
        classes = {
            self.OK:      "success",
            self.WARNING: "warning",
            self.ERROR:   "danger"
        }
        return classes[self]

    def __str__(self):
        return self.css


@attr.s
class IncidentManager(object):
    path = attr.ib()

    last_alert       = attr.ib(default="")
    active_alerts    = attr.ib(factory=dict)
    expired          = attr.ib(factory=defer.Deferred)
    _timeout         = attr.ib(factory=defer.Deferred)
    _alert_timeouts  = attr.ib(factory=dict)  # alert name => timeout

    _monitoring_down = attr.ib(default=False)

    _logs            = attr.ib(factory=list)

    def process_heartbeats(self, heartbeats, timestamp):
        if heartbeats:
            self.last_updated = timestamp
            if self._monitoring_down:
                self._monitoring_down = False
                # Monitoring is back up, re-activate timeout
                # TODO: Get IncidentClosing timeout from settings?
                #       Defaulting to 1h
                self._timeout = task.deferLater(reactor, 3600, self._expire)
                self.log_event('[Meta]MonitoringUp', timestamp)

    def process_alerts(self, alerts, timestamp):
        # TODO: Get IncidentClosing timeout from settings?
        #       Defaulting to 1h
        if alerts:
            self._timeout.cancel()
            self._timeout = task.deferLater(reactor, 3600, self._expire)
            self.last_alert = timestamp
        for alert in alerts:
            alertname = alert.labels.alertname
            if alertname in self._alert_timeouts:
                self._alert_timeouts[alertname].cancel()
            self._alert_timeouts[alertname] = task.deferLater(
                reactor, 5*60, self._expire_alert, alertname)

        new_alerts = {alert.labels.alertname: alert
                      for alert in alerts
                      if alert.labels.alertname not in self._alert_timeouts}

        if new_alerts:
            self.log_event('New', timestamp, new_alerts.values())

        self.active_alerts.update(new_alerts)

    def _expire(self):
        if not self._monitoring_down:
            self.expired.callback(self)

    def _expire_alert(self, alertname):
        self.log_event('Resolved', current_timestamp(), self.active_alerts[alertname])
        del self.active_alerts[alertname]

    def monitoring_down(self, timestamp):
        self._monitoring_down = True
        self.log_event('[Meta]MonitoringDown', timestamp)

    def log_event(self, message, timestamp, alerts=[]):
        obj = {"message": message, "timestamp": timestamp}
        if alerts:
            alerts = copy.deepcopy(alerts)
            for alert in alerts:
                alert.status = alert.status.css
            obj["alerts"] = alerts
        self._logs.append(obj)
        # Persist messages
        with self.path.open('w') as f:
            m = Munch.fromDict({"log": self._logs, "timestamp": timestamp})
            f.write(m.toYAML().encode("utf-8"))

    def component_status(self, component):
        return max((alert.status
                    for alert in self.active_alerts.values()
                    if alert.labels.alertname == component),
                   default=Severity.OK)
