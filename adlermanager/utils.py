import attr
import functools
import rfc3339
import dateutil.parser
from datetime import datetime, timezone
from twisted.python.filepath import FilePath

@attr.s
class TimestampFile(object):
    path = attr.ib()

    def set(self, time):
        with self.path.open('w') as f:
            f.write(rfc3339.format(time).encode('utf-8'))

    def now(self):
        self.set(datetime.now(timezone.utc))

    def get(self):
        if self.path.exists():
            with self.path.open('r') as f:
                return dateutil.parser.parse(f.read().decode('utf-8'))
        else:
            return None


def ensure_dirs(path):
    path.makedirs(ignoreExistingDirectory=True)


def as_list(f):
    """Decorator that changes a generator into a function that returns a list."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return list(f(*args, **kwargs))
    return wrapper
