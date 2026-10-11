"""Usage:  python cli.py sample_data/*.json [--json]"""
import argparse
import json
import sys

from fhir_validator import validate_file

ICON = {"error": "✗", "warning": "!"}


def main() -> int:
    ap = argparse.ArgumentParser(description="FHIR clinical data validator")
    ap.add_argument("files", nargs="+", help="FHIR JSON files")
    ap.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = ap.parse_args()

    reports = [(f, validate_file(f)) for f in args.files]

    if args.json:
        print(json.dumps({f: r.to_dict() for f, r in reports}, indent=2))
    else:
        for f, r in reports:
            status = "VALID" if r.is_valid else "INVALID"
            print(f"\n{f}  [{r.resource_type}/{r.resource_id}]  -> {status} "
                  f"({len(r.errors)} errors, {len(r.warnings)} warnings)")
            for i in r.issues:
                print(f"   {ICON[i.severity.value]} {i.rule:<11} {i.location}: {i.message}")

    return 0 if all(r.is_valid for _, r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
