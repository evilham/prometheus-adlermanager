from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, Optional, cast

import attr

from .utils import current_time, read_timestamp


class Severity(IntEnum):
    OK = 0
    WARNING = 1
    ERROR = 2

    @classmethod
    def from_string(cls, s: str) -> "Severity":
        # TODO: Do something sensitive with other priorities
        #       At least document them somewhere :-D
        labels = {
            "ok": cls.OK,
            "warning": cls.WARNING,
            "error": cls.ERROR,
            "critical": cls.ERROR,
        }
        return labels[s.lower()]

    @classmethod
    def from_alert(cls, alert: "Alert") -> "Severity":
        if alert.endsAt and alert.endsAt <= current_time():
            return Severity.OK
        return Severity.from_string(alert.labels.get("severity", "OK"))

    @property
    def css(self):
        classes = {self.OK: "success", self.WARNING: "warning", self.ERROR: "danger"}
        return classes[self]

    def __str__(self):
        return self.css


@attr.s
class Alert:
    labels: Dict[str, str] = attr.ib(factory=dict)
    annotations: Dict[str, str] = attr.ib(factory=dict)
    endsAt: Optional[datetime] = attr.ib(default=None)
    startsAt: Optional[datetime] = attr.ib(default=None)
    status: Severity = attr.ib(default=Severity.OK)

    @classmethod
    def import_alert(cls, d: Dict[str, Any]) -> "Alert":
        # Convert date data types
        alert = Alert(
            labels=d.get("labels", dict()),
            annotations=d.get("annotations", dict()),
        )
        for att in ["startsAt", "endsAt"]:
            if att in d:
                try:
                    setattr(alert, att, read_timestamp(cast(str, d[att])))
                except Exception:
                    setattr(alert, att, None)
        # Convert severity (needs date data)
        alert.status = Severity.from_alert(alert)
        return alert
