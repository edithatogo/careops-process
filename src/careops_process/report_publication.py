# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Atomic publication of a validated analytical report in its approved directory."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


def publish_report(report: Mapping[str, object], output: Path) -> None:
    """Stage, flush and replace a report without exposing partial output.

    The caller supplies an approved directory. A failed serialization or
    replacement preserves any prior report and removes the staged file.
    """
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=".careops-report-",
            suffix=".json",
            delete=False,
        ) as handle:
            staged = Path(handle.name)
            json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        staged.replace(output)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
