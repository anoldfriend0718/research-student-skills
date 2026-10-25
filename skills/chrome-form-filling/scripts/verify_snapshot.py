"""Compare complete local form snapshots. Never accesses a browser or network."""
import argparse
import json
from pathlib import Path


def validate(rows):
    if not isinstance(rows, list):
        raise ValueError("Snapshot must be a list of records")
    keys = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"key", "fields"}:
            raise ValueError("Each record must contain exactly key and fields")
        if not isinstance(row["key"], str) or not row["key"].strip():
            raise ValueError("Record key must be a nonempty string")
        if not isinstance(row["fields"], dict):
            raise ValueError("Record fields must be an object")
        keys.append(row["key"])
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate record keys; resolve identity before comparison")
    return {row["key"]: row["fields"] for row in rows}


def compare(expected, actual, ignore_order=False):
    """Return strict field and membership differences, retaining null/zero distinctions."""
    exp, got = validate(expected), validate(actual)
    differences = []
    for key in exp.keys() - got.keys():
        differences.append({"key": key, "problem": "missing_record"})
    for key in got.keys() - exp.keys():
        differences.append({"key": key, "problem": "unexpected_record"})
    for key in exp.keys() & got.keys():
        for field in exp[key].keys() | got[key].keys():
            if field not in exp[key] or field not in got[key]:
                differences.append({"key": key, "field": field, "problem": "field_membership"})
            elif json.dumps(exp[key][field], sort_keys=True) != json.dumps(got[key][field], sort_keys=True):
                differences.append({"key": key, "field": field, "problem": "value",
                                    "expected": exp[key][field], "actual": got[key][field]})
    if not ignore_order and list(exp) != list(got):
        differences.append({"problem": "order", "expected": list(exp), "actual": list(got)})
    return sorted(differences, key=lambda x: (x.get("key", ""), x.get("field", ""), x["problem"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--ignore-order", action="store_true")
    args = parser.parse_args()
    try:
        expected = json.loads(args.expected.read_text(encoding="utf-8-sig"))
        actual = json.loads(args.actual.read_text(encoding="utf-8-sig"))
        differences = compare(expected, actual, args.ignore_order)
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps({"ok": not differences, "expected_count": len(expected),
                      "actual_count": len(actual), "differences": differences}, ensure_ascii=True))
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
