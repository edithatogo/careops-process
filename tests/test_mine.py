"""Synthetic conformance tests."""

import pytest

from careops_process.mine import conformance, discover_variants


def traces() -> list[tuple[str, ...]]:
    """Return a small synthetic process log."""
    return [("received", "decided"), ("received", "decided"), ("received", "escalated")]


def test_variants_are_frequency_ordered() -> None:
    """The dominant path is returned first."""
    assert discover_variants(traces())[0] == (("received", "decided"), 2)


def test_conformance_reports_deviation() -> None:
    """Deviation paths reduce fitness and remain inspectable."""
    result = conformance(traces(), reference=("received", "decided"))
    assert result.fitness == pytest.approx(5 / 6)
    assert result.precision == pytest.approx(2 / 3)
    assert result.deviations == ("received -> escalated",)


def test_empty_inputs_fail_closed() -> None:
    """A meaningless mining request is rejected."""
    with pytest.raises(ValueError, match="reference"):
        conformance(traces(), reference=())
    with pytest.raises(ValueError, match="traces"):
        conformance([], reference=("received",))
