from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Issue:
    severity: Severity
    location: str
    message: str
    rule: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class Report:
    resource_type: str = "unknown"
    resource_id: str = "-"
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "resourceType": self.resource_type,
            "id": self.resource_id,
            "valid": self.is_valid,
            "errorCount": len(self.errors),
            "warningCount": len(self.warnings),
            "issues": [i.to_dict() for i in self.issues],
        }
