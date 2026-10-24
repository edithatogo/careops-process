# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Complete-population acquisition contract tests."""

import pytest

from careops_process.acquisition import AcquisitionPage, TransientSourceError, acquire_partition


def fact(identifier: str) -> dict[str, object]:
    """Return a minimized synthetic source fact."""
    return {
        "id": identifier,
        "activity": "task_observed",
        "timestamp_utc": "2026-07-01T00:00:00Z",
        "source_system": "planner",
        "object_ids": [f"task:{identifier}"],
    }


def test_acquisition_exhausts_pages_and_reconciles_counts() -> None:
    """A complete run follows cursors until the source is exhausted."""
    pages: dict[str | None, AcquisitionPage] = {
        None: AcquisitionPage(records=(fact("1"), fact("2")), next_cursor="page-2"),
        "page-2": AcquisitionPage(records=(fact("3"),), next_cursor=None),
    }

    result = acquire_partition("planner", "assigned-tasks", pages.__getitem__)

    assert [item["id"] for item in result.facts] == ["1", "2", "3"]
    assert result.manifest.pages_read == len(pages)
    assert result.manifest.candidate_count == len(result.facts)
    assert result.manifest.acquired_count == len(result.facts)
    assert result.manifest.duplicate_count == 0
    assert result.manifest.rejected_count == 0
    assert result.manifest.exhausted is True
    assert len(result.manifest.content_hash) == len("0" * 64)


def test_acquisition_suppresses_replayed_ids_deterministically() -> None:
    """Overlapping pages cannot duplicate an event in the corpus."""
    pages: dict[str | None, AcquisitionPage] = {
        None: AcquisitionPage(records=(fact("1"), fact("2")), next_cursor="next"),
        "next": AcquisitionPage(records=(fact("2"), fact("3")), next_cursor=None),
    }

    result = acquire_partition("planner", "assigned-tasks", pages.__getitem__)

    assert [item["id"] for item in result.facts] == ["1", "2", "3"]
    assert result.manifest.candidate_count == sum(len(page.records) for page in pages.values())
    assert result.manifest.acquired_count == len(result.facts)
    assert result.manifest.duplicate_count == 1


def test_acquisition_rejects_prohibited_raw_fields() -> None:
    """Narrative and identity fields fail closed at the adapter boundary."""
    unsafe = fact("1") | {"subject": "protected narrative"}

    with pytest.raises(ValueError, match="prohibited"):
        acquire_partition(
            "outlook",
            "mailbox",
            lambda _: AcquisitionPage(records=(unsafe,), next_cursor=None),
        )


def test_acquisition_records_malformed_rows_without_persisting_payload() -> None:
    """Malformed rows produce minimized reasons rather than raw dead letters."""
    malformed: dict[str, object] = {"id": "bad", "activity": "task_observed"}

    result = acquire_partition(
        "planner",
        "assigned-tasks",
        lambda _: AcquisitionPage(records=(malformed, fact("ok")), next_cursor=None),
    )

    assert [item["id"] for item in result.facts] == ["ok"]
    assert result.manifest.rejected_count == 1
    assert result.dead_letters[0].fact_id == "bad"
    assert result.dead_letters[0].reason == "missing_required_fields"
    assert not hasattr(result.dead_letters[0], "payload")


def test_acquisition_detects_cursor_loop() -> None:
    """A cyclic next link cannot be mistaken for source exhaustion."""
    page = AcquisitionPage(records=(fact("1"),), next_cursor="same")

    with pytest.raises(ValueError, match="cursor loop"):
        acquire_partition("teams", "team-events", lambda _: page)


def test_acquisition_supports_withdrawn_partition() -> None:
    """Source withdrawal is explicit and emits no misleading empty corpus."""
    result = acquire_partition(
        "sharepoint",
        "site",
        lambda _: pytest.fail("withdrawn sources must not be fetched"),
        withdrawn=True,
    )

    assert result.facts == ()
    assert result.manifest.exhausted is False
    assert result.manifest.withdrawn is True
    assert result.manifest.candidate_count == 0


def test_acquisition_retries_transient_throttling() -> None:
    """A bounded transient retry can recover without changing reconciliation."""
    attempts = 0

    def fetch(_: str | None) -> AcquisitionPage:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            message = "throttled"
            raise TransientSourceError(message)
        return AcquisitionPage(records=(fact("1"),), next_cursor=None)

    delays: list[float] = []
    result = acquire_partition(
        "planner", "assigned-tasks", fetch, max_retries=1, sleep=delays.append
    )

    assert result.manifest.retry_count == 1
    assert result.manifest.acquired_count == 1
    assert delays == [1.0]


def test_acquisition_fails_after_retry_budget() -> None:
    """Persistent throttling cannot be reported as source exhaustion."""

    def fetch(_: str | None) -> AcquisitionPage:
        message = "throttled"
        raise TransientSourceError(message)

    with pytest.raises(TransientSourceError, match="throttled"):
        acquire_partition("planner", "assigned-tasks", fetch, max_retries=1)


def test_acquisition_applies_exclusive_watermark() -> None:
    """Events at or before the checkpoint are counted but not emitted."""
    old = fact("old") | {"timestamp_utc": "2026-06-30T23:59:59Z"}
    boundary = fact("boundary") | {"timestamp_utc": "2026-07-01T00:00:00Z"}
    new = fact("new") | {"timestamp_utc": "2026-07-01T00:00:01Z"}

    result = acquire_partition(
        "planner",
        "assigned-tasks",
        lambda _: AcquisitionPage(records=(old, boundary, new), next_cursor=None),
        watermark_utc="2026-07-01T00:00:00Z",
    )

    assert [item["id"] for item in result.facts] == ["new"]
    assert result.manifest.filtered_count == len((old, boundary))
    assert result.manifest.candidate_count == len((old, boundary, new))
