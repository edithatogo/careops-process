# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Enforce independent line and branch coverage from coverage.py XML counts."""

import sys
from pathlib import Path

from defusedxml import ElementTree


def main() -> int:
    """Reject missing measurements or either metric below the fixed 90% target."""
    try:
        report = ElementTree.parse(Path(sys.argv[1] if len(sys.argv) > 1 else "coverage.xml"))
        root = report.getroot()
        passed = True
        for label, prefix in (("Line", "lines"), ("Branch", "branches")):
            valid = int(root.attrib[f"{prefix}-valid"])
            covered = int(root.attrib[f"{prefix}-covered"])
            if valid <= 0 or not 0 <= covered <= valid:
                sys.stderr.write("Invalid coverage counts.\n")
                return 1
            sys.stdout.write(
                f"{label} coverage: {covered}/{valid} = {100 * covered / valid:.2f}%\n"
            )
            passed = passed and covered * 100 >= valid * 90
    except (OSError, ValueError, KeyError, ElementTree.ParseError) as error:
        sys.stderr.write(f"Invalid coverage report: {error}\n")
        return 1
    if not passed:
        sys.stderr.write("Line and branch coverage must each reach 90%.\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
