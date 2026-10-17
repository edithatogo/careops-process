"""Closed-run boundary for converting a reconciled backfill into OCEL output."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .backfill_evidence import validate_bound_evidence
from .pilot_gate import validate_pilot_entry
from .pipeline import PipelineResult, run_pipeline


def _fail(message: str) -> None:
    raise ValueError(message)


def run_closed_backfill(
    facts: list[dict[str, object]],
    evidence: dict[str, Any],
    *,
    pseudonym_secret: str,
    schema_version: str = "1.0.0",
    generated_at_utc: datetime | None = None,
) -> PipelineResult:
    """Run discovery only when a sanitized backfill evidence record is closed."""
    if evidence.get("evidence_class") == "live_corpus":
        _fail("live corpus execution requires supported authenticated evidence verification")
    required = ("run_id", "status", "folder_count", "page_count", "candidate_count")
    missing = [key for key in required if evidence.get(key) is None]
    if missing:
        _fail(f"closed-run evidence missing: {', '.join(missing)}")
    for field in ("folder_count", "page_count", "candidate_count"):
        count = evidence[field]
        if type(count) is not int or count < 0:
            _fail(f"{field} must be a non-negative integer")
    if evidence["status"] != "closed":
        _fail("process discovery requires a closed backfill run")
    gates = (
        "pagination_exhausted",
        "reconciled",
        "idempotency_replay_verified",
        "no_raw_content_stored",
    )
    if not all(evidence.get(gate) is True for gate in gates):
        _fail("closed-run completeness or privacy gate failed")
    if not facts:
        _fail("closed-run projection contains no minimized facts")
    lineage = validate_bound_evidence(facts, evidence)
    generated = generated_at_utc or datetime.now(UTC)
    result = run_pipeline(
        facts,
        log_id=str(evidence["run_id"]),
        schema_version=schema_version,
        pseudonym_secret=pseudonym_secret,
        generated_at_utc=generated,
        minimum_cohort_size=5,
    )
    result.log.lineage = lineage
    return result


def run_authorised_closed_backfill(  # noqa: PLR0913
    facts: list[dict[str, object]],
    evidence: dict[str, Any],
    pilot_entry: dict[str, Any],
    *,
    pseudonym_secret: str,
    schema_version: str = "1.0.0",
    generated_at_utc: datetime | None = None,
) -> PipelineResult:
    """Run a closed backfill only after the corpus pilot-entry gate passes."""
    validate_pilot_entry(pilot_entry)
    if pilot_entry.get("configuration_hash") != evidence.get("configuration_hash"):
        _fail("pilot approval must bind the run configuration hash")
    configuration = evidence.get("configuration")
    if not isinstance(configuration, dict) or (
        configuration.get("authorised_source_partitions")
        != pilot_entry["authorised_source_partitions"]
    ):
        _fail("pilot approval scope must match the frozen run configuration")
    return run_closed_backfill(
        facts,
        evidence,
        pseudonym_secret=pseudonym_secret,
        schema_version=schema_version,
        generated_at_utc=generated_at_utc,
    )
