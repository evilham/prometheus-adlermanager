from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, Optional, Union, cast

import attr
import yaml

from .utils import current_time, read_timestamp


class Severity(IntEnum):
    OK = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

    @classmethod
    def from_string(cls, s: str) -> "Severity":
        # TODO: Do something sensitive with other priorities
        #       At least document them somewhere :-D
        labels = {
            "ok": cls.OK,
            "info": cls.INFO,
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
    def css(self) -> str:
        classes = {self.OK: "success", self.WARNING: "warning", self.ERROR: "danger"}
        return classes[self]

    def __str__(self) -> str:
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


@attr.s
class SiteConfig(object):
    message: str = attr.ib(default="")
    force_state: bool = attr.ib(default=False)

    @property
    def title(self) -> str:
        parts = self.message.split("\n\n")
        if len(parts) < 2:
            return ""
        return parts[0]

    @property
    def body(self) -> str:
        parts = self.message.split("\n\n")
        if len(parts) < 2:
            return self.message
        return parts[1]

    @property
    def state_is_forced(self) -> bool:
        if self.message is None or self.message == "":
            return False
        return self.force_state

    def to_YAML(self) -> str:
        return yaml.safe_dump(attr.asdict(self), allow_unicode=True)

    @classmethod
    def from_YAML(cls, yaml_string: Union[bytes, str]) -> "SiteConfig":
        """
        Create a SiteConfig object from a YAML string / bytes.

        Args:
            yaml_string (str): The YAML string representing our SiteConfig.

        Returns:
            SiteConfig: The SiteConfig represented by yaml_string.
        """
        obj = yaml.safe_load(yaml_string)
        return SiteConfig(**obj)
