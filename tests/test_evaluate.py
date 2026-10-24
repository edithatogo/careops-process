# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic temporal and drift evaluation tests."""

import pytest

from careops_process.evaluate import label_drift, temporal_split


def test_temporal_split_preserves_order() -> None:
    """Evaluation split keeps earlier observations in training."""
    train, test = temporal_split([1, 2, 3, 4, 5], train_fraction=0.6)
    assert train == [1, 2, 3]
    assert test == [4, 5]


def test_drift_reports_novel_labels() -> None:
    """Novel process labels trigger review even when divergence is small."""
    report = label_drift(["a", "a", "b"], ["a", "c", "c"])
    assert report.novel_labels == ("c",)
    assert report.drifted


def test_invalid_evaluation_inputs_fail_closed() -> None:
    """Invalid splits and empty populations are rejected."""
    with pytest.raises(ValueError, match="train_fraction"):
        temporal_split([1, 2], train_fraction=1.0)
    with pytest.raises(ValueError, match="empty"):
        label_drift([], ["a"])
