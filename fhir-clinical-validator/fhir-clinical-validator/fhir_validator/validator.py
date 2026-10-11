"""Two-layer validation:
   1. Structural  - resource conforms to the FHIR spec (via fhir.resources / pydantic)
   2. Clinical    - business rules in rules.py (dates, units, plausible ranges, references)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fhir.resources import get_fhir_model_class
from pydantic import ValidationError

from .models import Issue, Report, Severity
from .rules import RULES
from .utils import iter_references


def validate_structure(data: dict) -> list[Issue]:
    rtype = data.get("resourceType")
    if not rtype:
        return [Issue(Severity.ERROR, "resourceType", "Missing 'resourceType'.", "STRUCT-001")]
    try:
        model = get_fhir_model_class(rtype)
    except Exception:
        return [Issue(Severity.ERROR, "resourceType", f"Unknown resource type '{rtype}'.", "STRUCT-002")]

    parse = getattr(model, "model_validate", None) or model.parse_obj  # pydantic v2 / v1
    try:
        parse(data)
    except ValidationError as exc:
        return [
            Issue(Severity.ERROR, ".".join(str(p) for p in err["loc"]) or rtype, err["msg"], "STRUCT-003")
            for err in exc.errors()
        ]
    return []


def validate_clinical(data: dict) -> list[Issue]:
    issues: list[Issue] = []
    for rule in RULES.get(data.get("resourceType", ""), []):
        issues.extend(rule(data))
    return issues


def _validate_bundle(bundle: dict) -> list[Issue]:
    issues: list[Issue] = []
    entries = bundle.get("entry", []) or []

    known = set()
    for e in entries:
        res = e.get("resource", {})
        if e.get("fullUrl"):
            known.add(e["fullUrl"])
        if res.get("resourceType") and res.get("id"):
            known.add(f"{res['resourceType']}/{res['id']}")

    for i, e in enumerate(entries):
        res = e.get("resource")
        if not res:
            issues.append(Issue(Severity.ERROR, f"Bundle.entry[{i}]", "Entry has no resource.", "BUN-001"))
            continue
        sub = validate_resource(res)
        for issue in sub.issues:
            issue.location = f"entry[{i}]({sub.resource_type}).{issue.location}"
            issues.append(issue)
        for path, ref in iter_references(res):
            if not ref.startswith(("http", "#")) and ref not in known:
                issues.append(Issue(Severity.WARNING, f"entry[{i}].{path}",
                                    f"Reference '{ref}' not found inside the bundle.", "BUN-002"))
    return issues


def validate_resource(data: dict[str, Any]) -> Report:
    report = Report(data.get("resourceType", "unknown"), data.get("id", "-"))

    structural = validate_structure(data)
    report.issues.extend(structural)
    if any(i.rule in ("STRUCT-001", "STRUCT-002") for i in structural):
        return report  # nothing more we can check

    if data.get("resourceType") == "Bundle":
        report.issues.extend(_validate_bundle(data))
    else:
        report.issues.extend(validate_clinical(data))
    return report


def validate_file(path: str | Path) -> Report:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Report("unknown", str(path), [Issue(Severity.ERROR, str(path), f"Cannot read JSON: {exc}", "IO-001")])
    return validate_resource(data)
