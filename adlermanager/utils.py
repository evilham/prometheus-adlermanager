from datetime import datetime, timezone

import attr
from twisted.python.filepath import FilePath

_blessed_date_format = "%Y-%m-%dT%H:%M:%S%z"


@attr.s
class TimestampFile(object):
    path: FilePath = attr.ib()

    def set(self, time: datetime) -> None:
        with self.path.open("w") as f:
            f.write(time.strftime(_blessed_date_format).encode("utf-8"))

    def now(self):
        self.set(current_time())

    def getStr(self):
        if not self.path.exists():
            return ""
        with self.path.open("r") as f:
            return f.read().decode("utf-8")


def current_time():
    return datetime.now(timezone.utc)


def current_timestamp():
    return current_time().strftime(_blessed_date_format)


def read_timestamp(s: str) -> datetime:
    # We drop nanoseconds as python does not support that
    return datetime.strptime(f"{s.split('.')[0]}+00:00", _blessed_date_format)


def ensure_dirs(path: FilePath) -> None:
    path.makedirs(ignoreExistingDirectory=True)
