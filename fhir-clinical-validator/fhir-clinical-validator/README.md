# FHIR-Based Clinical Data Validation

A small Python project that validates FHIR JSON resources in two layers:

1. **Structural validation** – checks the resource against the FHIR specification using `fhir.resources`.
2. **Clinical validation** – custom business rules (`fhir_validator/rules.py`):
   - Patient: identity present, valid gender code, birth date not in the future, death after birth
   - Observation: subject required, value present, no future dates, UCUM unit + plausible range for vitals (LOINC)
   - Condition: subject, clinical status, coding system
   - Bundle: validates every entry and flags references that do not resolve inside the bundle

## Setup
```bash
pip install -r requirements.txt
```

## Run
```bash
python cli.py sample_data/*.json          # human-readable report
python cli.py sample_data/*.json --json   # JSON report
pytest -q                                 # tests
```
Exit code is `1` if any resource has errors (CI-friendly).

## Use as a library
```python
from fhir_validator import validate_resource
report = validate_resource({"resourceType": "Patient", "gender": "male"})
print(report.is_valid, [i.message for i in report.issues])
```

## Extending
Add a function `def my_rule(res: dict) -> list[Issue]` in `rules.py` and register it in `RULES["ResourceType"]`.
Ideas for next steps: FastAPI endpoint, terminology validation (SNOMED/LOINC servers), HAPI FHIR `$validate` integration, profile (StructureDefinition) validation.
