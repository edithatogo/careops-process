# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Fail-closed governance and reconstruction cases identified by branch measurement."""

import pytest

from careops_process.correlation import CorrelationHypothesis, build_ocel_from_facts
from careops_process.governance import validate_executive_record
from careops_process.ocel import ContractError, OcelObject, OcelRelation, validate_ocel
from tests.test_governance import record
from tests.test_ocel import sample_log
from tests.test_reconstruct import multi_source_facts


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_id", None, "missing governance"),
        ("run_id", 1, "non-empty string"),
        ("owner_validation", [], "must be an object"),
        ("scope_approved", 1, "boolean"),
        ("ig_approved", 1, "boolean"),
    ],
)
def test_governance_rejects_incoherent_field_types(field: str, value: object, message: str) -> None:
    """Missing and mistyped evidence never satisfy governance gates."""
    candidate = record()
    candidate[field] = value
    with pytest.raises(ValueError, match=message):
        validate_executive_record(candidate)


def test_governance_rejects_non_record_and_incomplete_owner() -> None:
    """An approved scope still requires completed owner validation."""
    with pytest.raises(ValueError, match="dictionary"):
        validate_executive_record([])
    candidate = record()
    candidate.update(scope_approved=True, ig_approved=True, executive_decision="pause")
    with pytest.raises(ValueError, match="requires owner validation"):
        validate_executive_record(candidate)
    candidate["owner_validation"]["status"] = "complete"
    validate_executive_record(candidate)
    candidate["ig_approved"] = False
    with pytest.raises(ValueError, match="scope and IG"):
        validate_executive_record(candidate)


def test_governance_rejects_unknown_owner_status() -> None:
    """An unknown owner status cannot masquerade as pending or complete."""
    candidate = record()
    candidate["owner_validation"]["status"] = "approved"
    with pytest.raises(ValueError, match="owner validation status"):
        validate_executive_record(candidate)


@pytest.mark.parametrize(
    ("field", "value", "error", "message"),
    [
        ("object_types", [], TypeError, "must be a mapping"),
        ("object_types", {1: "task"}, TypeError, "string keys"),
        ("object_types", {"task:t1": 1}, TypeError, "string keys"),
        ("object_ids", [], ValueError, "non-empty list"),
        ("object_ids", "task:t1", ValueError, "non-empty list"),
        ("object_ids", [1], TypeError, "contain strings"),
        ("object_ids", ["bad-prefix"], ValueError, "type prefix"),
        ("timestamp_utc", 1, TypeError, "datetime or ISO"),
    ],
)
def test_reconstruction_rejects_malformed_source_facts(
    field: str,
    value: object,
    error: type[Exception],
    message: str,
) -> None:
    """Invalid source shapes fail before a plausible-looking corpus is produced."""
    facts = multi_source_facts()
    facts[0][field] = value
    with pytest.raises(error, match=message):
        build_ocel_from_facts(facts, log_id="invalid", lineage="synthetic")


def test_reconstruction_rejects_conflicting_explicit_types() -> None:
    """Two sources cannot silently assign different semantics to one object."""
    facts = multi_source_facts()
    facts[0]["object_types"] = {"governance:m1": "meeting"}
    facts[1]["object_types"] = {"governance:m1": "approval"}
    with pytest.raises(ValueError, match="conflicting explicit"):
        build_ocel_from_facts(facts, log_id="conflict", lineage="synthetic")


@pytest.mark.parametrize(
    ("target", "version", "message"),
    [("task:t1", "v1", "self-reference"), ("document:d1", " ", "rule version")],
)
def test_hypotheses_require_distinct_objects_and_rule_provenance(
    target: str,
    version: str,
    message: str,
) -> None:
    """A bounded confidence score alone does not establish usable inference."""
    with pytest.raises(ValueError, match=message):
        CorrelationHypothesis("task:t1", target, "possibly_concerns", 0.5, version)


@pytest.mark.parametrize("field", ["events", "objects"])
def test_ocel_rejects_duplicate_identities(field: str) -> None:
    """Duplicate source identities cannot inflate an admitted mining corpus."""
    log = sample_log()
    values = log.events if field == "events" else log.objects
    duplicated = log.model_copy(update={field: [*values, values[0]]})
    with pytest.raises(ContractError, match="must be unique"):
        validate_ocel(duplicated)


def test_ocel_rejects_unsafe_objects_and_naive_event_time() -> None:
    """Narrative identifiers and ambiguous local time cannot enter an OCEL log."""
    with pytest.raises(ValueError, match="safe, non-sensitive"):
        OcelObject(object_id="unsafe identity", object_type="request")
    event = sample_log().events[0].model_dump()
    event["timestamp_utc"] = sample_log().events[0].timestamp_utc.replace(tzinfo=None)
    with pytest.raises(ValueError, match="explicit timezone"):
        type(sample_log().events[0]).model_validate(event)


def test_ocel_relation_rejects_unknown_duplicate_and_unsafe_identity() -> None:
    """Relation integrity is checked independently of event-object references."""
    relation = OcelRelation(
        relation_id="relation-1",
        relation_type="concerns",
        source_object_id="req-1",
        target_object_id="person-1",
        observed_or_inferred="observed",
        confidence=1,
    )
    log = sample_log()
    with pytest.raises(ContractError, match="relation_id must be unique"):
        validate_ocel(log.model_copy(update={"relations": [relation, relation]}))
    unknown = relation.model_copy(update={"target_object_id": "missing"})
    with pytest.raises(ContractError, match="Unknown object reference"):
        validate_ocel(log.model_copy(update={"relations": [unknown]}))
    with pytest.raises(ValueError, match="safe, non-sensitive"):
        OcelRelation.model_validate(relation.model_dump() | {"relation_id": "unsafe id"})
