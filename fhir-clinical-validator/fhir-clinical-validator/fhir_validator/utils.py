"""Small helpers for working with FHIR dates and references."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator, Optional


def parse_fhir_date(value: Any) -> Optional[datetime]:
    """Parse FHIR date/dateTime (supports partial: YYYY, YYYY-MM). Returns aware UTC datetime or None."""
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 4:
            return datetime(int(value), 1, 1, tzinfo=timezone.utc)
        if len(value) == 7:
            year, month = value.split("-")
            return datetime(int(year), int(month), 1, tzinfo=timezone.utc)
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iter_references(node: Any, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield (path, reference-string) for every Reference found in a resource."""
    if isinstance(node, dict):
        ref = node.get("reference")
        if isinstance(ref, str):
            yield path or "reference", ref
        for key, val in node.items():
            if key != "reference":
                yield from iter_references(val, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from iter_references(item, f"{path}[{i}]")
