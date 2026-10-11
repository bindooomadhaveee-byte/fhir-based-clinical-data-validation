import json
from pathlib import Path

from fhir_validator import validate_file, validate_resource

DATA = Path(__file__).parent.parent / "sample_data"


def rules(report):
    return {i.rule for i in report.issues}


def test_valid_patient():
    assert validate_file(DATA / "patient_valid.json").is_valid


def test_invalid_patient_dates():
    r = validate_file(DATA / "patient_invalid.json")
    assert not r.is_valid
    assert {"PAT-004", "PAT-005"} <= rules(r)


def test_valid_observation():
    assert validate_file(DATA / "observation_valid.json").is_valid


def test_invalid_observation():
    r = validate_file(DATA / "observation_invalid.json")
    assert {"OBS-001", "OBS-004", "OBS-005"} <= rules(r)


def test_structural_error_bad_date_format():
    p = json.loads((DATA / "patient_valid.json").read_text())
    p["birthDate"] = "14/05/1990"
    assert "STRUCT-003" in rules(validate_resource(p))


def test_invalid_gender_code():
    p = json.loads((DATA / "patient_valid.json").read_text())
    p["gender"] = "banana"
    assert "PAT-006" in rules(validate_resource(p))


def test_unknown_resource_type():
    assert "STRUCT-002" in rules(validate_resource({"resourceType": "Foo"}))


def test_missing_resource_type():
    assert "STRUCT-001" in rules(validate_resource({}))


def test_bundle_checks():
    r = validate_file(DATA / "bundle_sample.json")
    assert "OBS-005" in rules(r)   # implausible systolic BP
    assert "BUN-002" in rules(r)   # dangling reference
