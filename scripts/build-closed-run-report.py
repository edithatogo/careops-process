"""Build a governed report from a closed, sanitized Outlook backfill export."""  # noqa: N999

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from careops_process.report import build_authorised_closed_run_report


def main() -> int:
    """Read sanitized inputs and write one deterministic report JSON file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--pilot-entry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    secret = os.environ.get("CAREOPS_PSEUDONYM_SECRET")
    if not secret:
        parser.error("CAREOPS_PSEUDONYM_SECRET must be set; no default secret is permitted")
    facts: list[dict[str, object]] = json.loads(args.facts.read_text(encoding="utf-8"))
    evidence: dict[str, Any] = json.loads(args.evidence.read_text(encoding="utf-8"))
    pilot_entry: dict[str, Any] = json.loads(args.pilot_entry.read_text(encoding="utf-8"))
    report = build_authorised_closed_run_report(
        facts, evidence, pilot_entry, pseudonym_secret=secret
    )
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
