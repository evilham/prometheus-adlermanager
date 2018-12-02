import attr
import json
import rfc3339
from datetime                import datetime
from enum                    import IntEnum
from munch                   import Munch
from twisted.python.filepath import FilePath
from twisted.internet        import reactor, defer, task

from .Config import Config
from .utils  import ensure_dirs, TimestampFile

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


@attr.s
class IncidentManager(object):
    path = attr.ib()

    expired          = attr.ib(factory=defer.Deferred)
    _timeout         = attr.ib(factory=defer.Deferred)
    alerts           = attr.ib(factory=list)

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
            self.last_alert = timestamp
            self._timeout.cancel()
            self._timeout = task.deferLater(reactor, 3600, self._expire)

        old_names = set((alert.labels.alertname for alert in self.alerts))
        alerts_names = set((alert.labels.alertname for alert in alerts))
        # Partition alerts in:
        preexisting_names = old_names.intersection(alerts_names)
        new_names = alerts_names.difference(old_names)
        absent_names = old_names.difference(alerts_names)

        self.alerts = alerts

        # TODO: log new and absent
        if absent_names:
            absent_alerts = [alert for alert in alerts
                             if alert.labels.alertname in absent_names]
            self.log_event('Resolved', timestamp, absent_alerts)
        if new_names:
            new_alerts = [alert for alert in alerts
                          if alert.labels.alertname in new_names]
            self.log_event('New', timestamp, new_alerts)

    def _expire(self):
        if not self._monitoring_down:
            self.expired.callback(self)

    def monitoring_down(self, timestamp):
        self._monitoring_down = True
        self.log_event('[Meta]MonitoringDown', timestamp)

    def log_event(self, message, timestamp, alerts=[]):
        obj = {"message": message, "timestamp": timestamp}
        if alerts:
            obj["alerts"] = alerts
        self._log.append(obj)
        # Persist messages
        with self.path.open('w') as f:
            m = Munch.fromDict({"log": self._log, "timestamp": timestamp})
            f.write(m.toYAML().encode("utf-8"))

    def component_status(self, component):
        return max((alert.status
                    for alert in self.alerts
                    if alert.labels.alertname == component),
                   default=Severity.OK)
