# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic semantic projection tests."""

from datetime import UTC, datetime

import pytest

from careops_process.discover import DiscoveryFamily
from careops_process.projection import build_projection
from careops_process.testsupport import sample_ocel_log


def test_projection_suppresses_small_cohorts() -> None:
    """Sparse logs retain quality counts but hide detail rows."""
    result = build_projection(
        sample_ocel_log(),
        families=[DiscoveryFamily("family-1", "approval", ("request-1",), 1.0)],
        generated_at_utc=datetime(2026, 1, 3, tzinfo=UTC),
        minimum_cohort_size=5,
    )
    assert result["quality"]["suppressed_small_cohort"] is True
    assert result["activities"] == []
    assert result["quality"]["event_count"] == 1


def test_projection_emits_deterministic_detail() -> None:
    """Adequate cohorts expose sorted activity and family rows."""
    log = sample_ocel_log().model_copy(update={"events": sample_ocel_log().events * 5})
    result = build_projection(
        log,
        families=[],
        generated_at_utc=datetime(2026, 1, 3, tzinfo=UTC),
        minimum_cohort_size=5,
    )
    assert result["activities"][0]["activity"] == "request_received"
    assert result["quality"]["suppressed_small_cohort"] is False


def test_projection_requires_aware_time_and_positive_threshold() -> None:
    """Projection controls fail closed."""
    with pytest.raises(ValueError, match="timezone"):
        build_projection(sample_ocel_log(), families=[], generated_at_utc=datetime(2026, 1, 3))  # noqa: DTZ001
    with pytest.raises(ValueError, match="positive"):
        build_projection(
            sample_ocel_log(),
            families=[],
            generated_at_utc=datetime(2026, 1, 3, tzinfo=UTC),
            minimum_cohort_size=0,
        )
