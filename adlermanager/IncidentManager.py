import attr
import rfc3339
import json
from datetime import datetime
from munch    import Munch

from .Config          import Config
from twisted.python.filepath import FilePath

FILENAME_TIME_FORMAT = '%Y-%m-%d-%H%MZ'

def ensure_dirs(path):
    path.makedirs(ignoreExistingDirectory=True)

@attr.s
class IncidentManager(object):
    incidents_dir = attr.ib()

    def get_or_create_incident(self, time):
        last_incident = max(self.incidents_dir.listdir())
        last_incident_time = datetime.strptime(FILENAME_TIME_FORMAT)
        if now - last_incident_time >= Config.new_incident_timeout:
            last_incident_time = now
            last_incident = last_incident_time.strftime(FILENAME_TIME_FORMAT)
        incident_dir = incidents_dir.child(last_incident)
        ensure_dirs(incident_dir)
        return incident_dir

    def save_alert(alert, time):
        incident_dir = get_or_create_incident(time)
        alerts_dir = incident_dir.child('alerts')
        ensure_dirs(alerts_dir)
        alert_file = alerts_dir.child(time.strftime(FILENAME_TIME_FORMAT)+'.json')
        with alert_file.open('w'):
            alert_file.write(json.dumps(alert))

    def get_last_incidents(self, count=5):
        raise NotImplementedError  # TODO
