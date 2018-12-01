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


@attr.s
class IncidentManager(object):
    incidents_dir = attr.ib()

    expired = attr.ib(factory=defer.Deferred)
    _timeout = attr.ib(factory=defer.Deferred)

    def process_alert(self, alert, timestamp):
        self._timeout.cancel()
        # TODO: Get timeout from settings?
        self._timeout = task.deferLater(reactor, 30*60, self._expire)

    def _expire(self):
        self.expired.callback(self)

    def maybe_get_current_incident(self):
        last = self.get_last_incident()
        last_incident_time = datetime.strptime(FILENAME_TIME_FORMAT)
        if time - last_incident_time >= Config.new_incident_timeout:
            return last
        else:
            return None

    def get_last_incident(self):
        return max(self.incidents_dir.listdir(), default=None)



    def save_alert(alert, time):
        incident_dir = get_or_create_incident(time)
        alerts_dir = incident_dir.child('alerts')
        ensure_dirs(alerts_dir)
        alert_file = alerts_dir.child(time.strftime(FILENAME_TIME_FORMAT)+'.json')
        with alert_file.open('w'):
            alert_file.write(json.dumps(alert))
        TimestampFile(incident_dir.child('last_alert.txt')).now()

    def get_last_incidents(self, count=5):
        if not self.incidents_dir.exists(): return []
        dirs = sorted(self.incidents_dir.listdir(), reverse=True)[:count]

    def is_incident_ongoing(self, incident):
        last_alert = TimestampFile(self.incidents_dir.child(incident).child('last_alert.txt'))

    def load_incident_info(self, incident):
        incident = Munch()
        incident.alerts = self.load_alerts(incident)
        return incident
