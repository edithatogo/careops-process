# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic discovery and active-learning tests."""

import pytest

from careops_process.discover import DiscoveryItem, active_learning_queue, discover_families


def items() -> list[DiscoveryItem]:
    """Return minimized labels with no message content."""
    return [
        DiscoveryItem("a", ("TESL request", "approval received"), "dataverse"),
        DiscoveryItem("b", ("TESL request", "approval decided"), "teams"),
        DiscoveryItem("c", ("leave request", "approval received"), "dataverse"),
    ]


def test_discovery_is_deterministic_and_explainable() -> None:
    """Families contain stable members and confidence values."""
    result = discover_families(items(), similarity_threshold=0.4)
    assert result[0].member_ids == ("a", "b", "c")
    assert result[0].confidence == pytest.approx(5 / 6)


def test_active_learning_prioritizes_low_confidence() -> None:
    """The review queue is bounded and confidence ordered."""
    result = discover_families(items(), similarity_threshold=0.9)
    assert active_learning_queue(result, limit=1) == ["family-1"]
    assert result[0].confidence == pytest.approx(0.25)


def test_invalid_threshold_and_limit_fail_closed() -> None:
    """Invalid discovery controls do not silently change output."""
    with pytest.raises(ValueError, match="threshold"):
        discover_families(items(), similarity_threshold=0.0)
    with pytest.raises(ValueError, match="negative"):
        active_learning_queue([], limit=-1)
