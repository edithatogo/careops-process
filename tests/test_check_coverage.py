# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Independent coverage thresholds must not be hidden by an aggregate score."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("covered_lines", "covered_branches", "expected"),
    [(100, 89, 1), (89, 100, 1), (90, 90, 0), (100, 100, 0)],
)
def test_separate_coverage_thresholds(
    tmp_path: Path,
    covered_lines: int,
    covered_branches: int,
    expected: int,
) -> None:
    """Each exact count must independently meet 90 percent, including the boundary."""
    report = tmp_path / "coverage.xml"
    report.write_text(
        f'<coverage lines-valid="100" lines-covered="{covered_lines}" '
        f'branches-valid="100" branches-covered="{covered_branches}"/>',
        encoding="utf-8",
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "scripts/check_coverage.py", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected
    assert "Line coverage:" in result.stdout
    assert "Branch coverage:" in result.stdout


@pytest.mark.parametrize(
    "xml",
    [
        "<broken",
        "<coverage/>",
        '<coverage lines-valid="0"/>',
        '<coverage lines-valid="100" lines-covered="101"/>',
        '<coverage lines-valid="100" lines-covered="-1"/>',
        '<coverage lines-valid="100" lines-covered="100" branches-valid="0" branches-covered="0"/>',
    ],
)
def test_missing_or_invalid_measurements_fail_closed(tmp_path: Path, xml: str) -> None:
    """A missing denominator or unreadable report cannot certify coverage."""
    report = tmp_path / "coverage.xml"
    report.write_text(xml, encoding="utf-8")
    result = subprocess.run(  # noqa: S603
        [sys.executable, "scripts/check_coverage.py", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
