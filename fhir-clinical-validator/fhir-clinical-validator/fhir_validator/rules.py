"""Clinical business rules that go beyond FHIR structural validation.

Each rule function takes a resource dict and returns a list of Issue objects.
Add new rules by writing a function and registering it in RULES.
"""
from __future__ import annotations

from typing import Callable

from .models import Issue, Severity
from .utils import now_utc, parse_fhir_date

ADMIN_GENDER = {"male", "female", "other", "unknown"}

# LOINC code -> (label, UCUM unit, min plausible, max plausible)
VITAL_RANGES = {
    "8867-4": ("Heart rate", "/min", 20, 300),
    "8310-5": ("Body temperature", "Cel", 25, 45),
    "8480-6": ("Systolic blood pressure", "mm[Hg]", 40, 300),
    "8462-4": ("Diastolic blood pressure", "mm[Hg]", 20, 200),
    "59408-5": ("Oxygen saturation", "%", 50, 100),
    "9279-1": ("Respiratory rate", "/min", 4, 80),
    "29463-7": ("Body weight", "kg", 0.3, 500),
    "8302-2": ("Body height", "cm", 20, 280),
}


def _loinc_codes(code_concept: dict) -> list[str]:
    return [
        c.get("code")
        for c in (code_concept or {}).get("coding", [])
        if c.get("system") == "http://loinc.org" and c.get("code")
    ]


# ---------------------------------------------------------------- Patient
def patient_identity(res: dict) -> list[Issue]:
    issues = []
    if not res.get("identifier") and not res.get("name"):
        issues.append(Issue(Severity.ERROR, "Patient", "Patient needs at least an identifier or a name.", "PAT-001"))
    if not res.get("gender"):
        issues.append(Issue(Severity.WARNING, "Patient.gender", "Gender is missing.", "PAT-002"))
    elif res["gender"] not in ADMIN_GENDER:
        issues.append(Issue(Severity.ERROR, "Patient.gender",
                            f"'{res['gender']}' is not a valid code (allowed: {', '.join(sorted(ADMIN_GENDER))}).", "PAT-006"))
    if not res.get("birthDate"):
        issues.append(Issue(Severity.WARNING, "Patient.birthDate", "Birth date is missing.", "PAT-003"))
    return issues


def patient_dates(res: dict) -> list[Issue]:
    issues = []
    birth = parse_fhir_date(res.get("birthDate"))
    if birth and birth > now_utc():
        issues.append(Issue(Severity.ERROR, "Patient.birthDate", "Birth date is in the future.", "PAT-004"))
    deceased = parse_fhir_date(res.get("deceasedDateTime"))
    if birth and deceased and deceased < birth:
        issues.append(Issue(Severity.ERROR, "Patient.deceasedDateTime", "Death date is before birth date.", "PAT-005"))
    return issues


# ------------------------------------------------------------ Observation
def observation_subject(res: dict) -> list[Issue]:
    if not (res.get("subject") or {}).get("reference"):
        return [Issue(Severity.ERROR, "Observation.subject", "Observation must reference a patient (subject).", "OBS-001")]
    return []


def observation_has_result(res: dict) -> list[Issue]:
    has_value = any(k.startswith("value") for k in res) or res.get("component")
    if not has_value and not res.get("dataAbsentReason"):
        return [Issue(Severity.WARNING, "Observation.value[x]", "No value and no dataAbsentReason.", "OBS-002")]
    return []


def observation_dates(res: dict) -> list[Issue]:
    eff = parse_fhir_date(res.get("effectiveDateTime"))
    if eff and eff > now_utc():
        return [Issue(Severity.ERROR, "Observation.effectiveDateTime", "Observation date is in the future.", "OBS-003")]
    return []


def observation_vital_ranges(res: dict) -> list[Issue]:
    """Check unit and plausible range for known vital-sign LOINC codes."""
    issues = []
    targets = []  # (code concept, quantity)
    if res.get("valueQuantity"):
        targets.append((res.get("code"), res["valueQuantity"]))
    for comp in res.get("component", []) or []:
        if comp.get("valueQuantity"):
            targets.append((comp.get("code"), comp["valueQuantity"]))

    for concept, qty in targets:
        for loinc in _loinc_codes(concept):
            if loinc not in VITAL_RANGES:
                continue
            label, unit, lo, hi = VITAL_RANGES[loinc]
            value = qty.get("value")
            if qty.get("code") and qty["code"] != unit:
                issues.append(Issue(Severity.ERROR, "Observation.valueQuantity.code",
                                    f"{label}: expected unit '{unit}', got '{qty['code']}'.", "OBS-004"))
            if isinstance(value, (int, float)) and not (lo <= value <= hi):
                issues.append(Issue(Severity.ERROR, "Observation.valueQuantity.value",
                                    f"{label}: value {value} outside plausible range {lo}-{hi} {unit}.", "OBS-005"))
    return issues


# -------------------------------------------------------------- Condition
def condition_rules(res: dict) -> list[Issue]:
    issues = []
    if not (res.get("subject") or {}).get("reference"):
        issues.append(Issue(Severity.ERROR, "Condition.subject", "Condition must reference a patient.", "CON-001"))
    if not res.get("clinicalStatus"):
        issues.append(Issue(Severity.WARNING, "Condition.clinicalStatus", "clinicalStatus is missing.", "CON-002"))
    codings = (res.get("code") or {}).get("coding", [])
    if not any(c.get("system") for c in codings):
        issues.append(Issue(Severity.WARNING, "Condition.code", "Condition code has no coding system (e.g. SNOMED CT / ICD-10).", "CON-003"))
    return issues


RULES: dict[str, list[Callable[[dict], list[Issue]]]] = {
    "Patient": [patient_identity, patient_dates],
    "Observation": [observation_subject, observation_has_result, observation_dates, observation_vital_ranges],
    "Condition": [condition_rules],
}
