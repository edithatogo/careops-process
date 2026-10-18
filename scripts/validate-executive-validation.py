# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Validate a sanitized governance and executive decision record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from careops_process.governance import validate_executive_record


def main() -> int:
    """Validate one JSON decision record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    record: dict[str, Any] = json.loads(args.path.read_text(encoding="utf-8"))
    validate_executive_record(record)
    sys.stdout.write("Executive validation record passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
