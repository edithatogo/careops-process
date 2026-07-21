"""Validate a sanitized governance and executive decision record."""  # noqa: N999

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _fail(message: str) -> None:
    raise ValueError(message)


def validate(record: dict[str, Any]) -> None:
    """Fail closed unless the record has all governance decision fields."""
    required = (
        "run_id",
        "evidence_reference",
        "scope_approved",
        "ig_approved",
        "owner_validation",
        "executive_decision",
    )
    missing = [key for key in required if record.get(key) is None]
    if missing:
        _fail(f"missing governance fields: {', '.join(missing)}")
    if not isinstance(record["owner_validation"], dict):
        _fail("owner_validation must be an object")
    if record["executive_decision"] != "pending":
        if record["scope_approved"] is not True or record["ig_approved"] is not True:
            _fail("executive decision requires scope and IG approval")
        if record["owner_validation"].get("status") != "complete":
            _fail("executive decision requires owner validation")


def main() -> int:
    """Validate one JSON decision record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    record: dict[str, Any] = json.loads(args.path.read_text(encoding="utf-8"))
    validate(record)
    sys.stdout.write("Executive validation record passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
