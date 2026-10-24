# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Build a governed report from a closed, sanitized Outlook backfill export."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, cast

from careops_process.report import build_authorised_closed_run_report
from careops_process.report_publication import publish_report


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
    try:
        if args.output.resolve() in {
            args.facts.resolve(),
            args.evidence.resolve(),
            args.pilot_entry.resolve(),
        }:
            parser.error("report output must be separate from its authoritative inputs")
        raw_facts: object = json.loads(args.facts.read_text(encoding="utf-8"))
        raw_evidence: object = json.loads(args.evidence.read_text(encoding="utf-8"))
        raw_entry: object = json.loads(args.pilot_entry.read_text(encoding="utf-8"))
        if not isinstance(raw_facts, list) or not all(
            isinstance(fact, dict) for fact in cast("list[object]", raw_facts)
        ):
            parser.error("facts input must be an array of minimized records")
        if not isinstance(raw_evidence, dict) or not isinstance(raw_entry, dict):
            parser.error("evidence and pilot-entry inputs must be objects")
        facts = cast("list[dict[str, object]]", raw_facts)
        evidence = cast("dict[str, Any]", raw_evidence)
        pilot_entry = cast("dict[str, Any]", raw_entry)
        report = build_authorised_closed_run_report(
            facts, evidence, pilot_entry, pseudonym_secret=secret
        )
    except OSError, ValueError, TypeError:
        parser.error(
            "closed-run inputs failed validation; inspect them in the approved evidence store"
        )
    try:
        publish_report(report, args.output)
    except OSError, ValueError, TypeError:
        parser.error("report publication failed; previous output was preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
