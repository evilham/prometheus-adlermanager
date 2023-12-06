from datetime import datetime, timezone

import attr
from twisted.internet import defer
from twisted.python.failure import Failure
from twisted.python.filepath import FilePath

_blessed_date_format = "%Y-%m-%dT%H:%M:%S%z"


@attr.s
class TimestampFile(object):
    path: FilePath = attr.ib()

    def set(self, time: datetime) -> None:
        with self.path.open("w") as f:
            f.write(time.strftime(_blessed_date_format).encode("utf-8"))

    def now(self) -> None:
        self.set(current_time())

    def getStr(self) -> str:
        if not self.path.exists():
            return ""
        with self.path.open("r") as f:
            return f.read().decode("utf-8")


def current_time() -> datetime:
    return datetime.now(timezone.utc)


def current_timestamp() -> str:
    return current_time().strftime(_blessed_date_format)


def read_timestamp(s: str) -> datetime:
    # We drop nanoseconds as python does not support that
    return datetime.strptime(f"{s.split('.')[0]}+00:00", _blessed_date_format)


def ensure_dirs(path: FilePath) -> None:
    path.makedirs(ignoreExistingDirectory=True)


def default_errback(failure: Failure) -> None:
    failure.trap(defer.CancelledError)  # type: ignore
    pass


def noop_deferred() -> defer.Deferred[None]:
    d: defer.Deferred[None] = defer.Deferred()
    _ = d.addErrback(default_errback)
    return d
