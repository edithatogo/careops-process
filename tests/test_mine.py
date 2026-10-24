# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic conformance tests."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

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


@pytest.mark.parametrize(
    ("observed", "reference", "fitness", "precision"),
    [
        ([()], ("a",), 0, 0),
        ([(), ("a",)], ("a",), 0.5, 1),
        ([("a", "a")], ("a",), 0.5, 1),
        ([("a",)], ("a", "a"), 0.5, 1),
        ([("b", "a")], ("a", "b"), 0, 1),
        ([("a", "b", "a")], ("a", "a", "b"), 1 / 3, 1),
        ([("x",)], ("a",), 0, 0),
    ],
)
def test_sequence_and_activity_metrics_have_distinct_meanings(
    observed: list[tuple[str, ...]],
    reference: tuple[str, ...],
    fitness: float,
    precision: float,
) -> None:
    """Empty paths and ordering affect positional fitness, not set-based precision."""
    result = conformance(observed, reference=reference)
    assert result.fitness == pytest.approx(fitness)
    assert result.precision == pytest.approx(precision)


def test_empty_variants_and_deviations_are_explicit() -> None:
    """Empty traces are excluded from variants but retained in deviation evidence."""
    result = conformance([(), ("b",), ("a",), ("b",), ()], reference=("a",))
    assert discover_variants([]) == []
    assert discover_variants([(), ()]) == []
    assert result.observed_variants == (("b",), ("a",))
    assert result.deviations == ("empty trace", "b", "b", "empty trace")
    assert discover_variants([("b",), ("a",)]) == [(("a",), 1), (("b",), 1)]


ACTIVITIES = st.sampled_from(["a", "b", "c"])
PATHS = st.lists(ACTIVITIES, max_size=10).map(tuple)


@given(st.lists(PATHS, min_size=1, max_size=20), st.lists(ACTIVITIES, min_size=1, max_size=10))
def test_conformance_is_bounded_deterministic_and_does_not_mutate(
    observed: list[tuple[str, ...]],
    reference: list[str],
) -> None:
    """Generated mixed traces preserve inputs and metrics under dataset permutation."""
    before = observed.copy(), reference.copy()
    result = conformance(observed, reference=reference)
    reversed_result = conformance(list(reversed(observed)), reference=reference)
    assert 0 <= result.fitness <= 1
    assert 0 <= result.precision <= 1
    assert result == conformance(observed, reference=reference)
    assert result.fitness == reversed_result.fitness
    assert result.precision == reversed_result.precision
    assert result.observed_variants == reversed_result.observed_variants
    assert result.deviations == tuple(reversed(reversed_result.deviations))
    assert (observed, reference) == before
    assert sum(count for _, count in discover_variants(observed)) == sum(map(bool, observed))


@given(st.lists(ACTIVITIES, min_size=1, max_size=10), st.integers(min_value=1, max_value=20))
def test_exact_replay_is_perfect_even_with_repeated_activities(
    reference: list[str],
    repetitions: int,
) -> None:
    """Repeated events retain their position and replay has no deviations."""
    result = conformance([reference] * repetitions, reference=reference)
    assert result.fitness == 1
    assert result.precision == 1
    assert result.deviations == ()
    assert discover_variants([reference] * repetitions) == [(tuple(reference), repetitions)]
