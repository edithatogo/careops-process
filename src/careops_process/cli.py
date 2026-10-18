# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Command-line smoke entry point for the synthetic CareOps pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .pipeline import run_pipeline

if TYPE_CHECKING:
    from collections.abc import Sequence


def _synthetic_facts() -> list[dict[str, object]]:
    return [
        {
            "id": "smoke-source-1",
            "activity": "request_received",
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "source_system": "synthetic",
            "object_ids": ["smoke-request-1"],
        },
        {
            "id": "smoke-source-2",
            "activity": "approval_decided",
            "timestamp_utc": "2026-01-02T00:00:00Z",
            "source_system": "synthetic",
            "object_ids": ["smoke-request-1"],
        },
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the synthetic pipeline and print its governed projection as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-id", default="synthetic-smoke")
    args = parser.parse_args(argv)
    secret = os.environ.get("CAREOPS_PSEUDONYM_SECRET")
    if not secret:
        parser.error("CAREOPS_PSEUDONYM_SECRET must be set; no default secret is permitted")
    result = run_pipeline(
        _synthetic_facts(),
        log_id=args.log_id,
        schema_version="1.0.0",
        pseudonym_secret=secret,
        generated_at_utc=datetime.now(UTC),
        reference=["request_received", "approval_decided"],
        minimum_cohort_size=1,
    )
    sys.stdout.write(json.dumps(result.projection, sort_keys=True) + "\n")
    return 0
