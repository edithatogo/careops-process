"""Contract artifact integrity tests."""

import json
from pathlib import Path


def test_connector_contract_is_strict_and_minimized() -> None:
    """The connector contract forbids arbitrary and raw-content fields."""
    contract = json.loads(Path("contracts/m365-fact-projection.json").read_text(encoding="utf-8"))
    fact = contract["properties"]["facts"]["items"]
    assert fact["additionalProperties"] is False
    assert "body" not in fact["properties"]
    assert "subject" not in fact["properties"]
    assert contract["properties"]["contract_version"]["const"] == "1.0.0"


def test_checkpoint_mapping_has_no_payload_columns() -> None:
    """The Dataverse mapping contains state, not source message payloads."""
    mapping = json.loads(
        Path("contracts/dataverse-checkpoint.mapping.json").read_text(encoding="utf-8")
    )
    assert all("body" not in column.lower() for column in mapping["columns"])
    assert mapping["privacy"]["raw_message_content"] == "prohibited"


def test_corpus_coverage_contract_preserves_unknown_tenant_denominator() -> None:
    """Coverage artifacts cannot claim a tenant-wide percentage."""
    contract = json.loads(
        Path("contracts/m365-corpus-coverage.schema.json").read_text(encoding="utf-8")
    )
    assert contract["additionalProperties"] is False
    assert contract["properties"]["tenant_wide_coverage"]["type"] == "null"
    partition = contract["properties"]["partitions"]["items"]
    assert partition["additionalProperties"] is False
    assert set(partition["required"]) >= {
        "candidate_count",
        "acquired_count",
        "permission_state",
        "provenance",
        "limitation",
    }


def test_corpus_coverage_contract_separates_evidence_classes() -> None:
    """Synthetic, smoke-test, and live-corpus outputs stay distinguishable."""
    contract = json.loads(
        Path("contracts/m365-corpus-coverage.schema.json").read_text(encoding="utf-8")
    )
    classes = contract["properties"]["evidence_class"]["enum"]
    assert classes == ["synthetic", "smoke_test", "live_corpus"]


def test_planner_export_is_paginated_pseudonymized_and_content_minimized() -> None:
    """The delegated Planner lane is exhaustive and persists no narrative."""
    script = Path("scripts/export-planner-corpus.ps1").read_text(encoding="utf-8")
    assert "@odata.nextLink" in script
    assert "HMACSHA256" in script
    assert "SHA256" in script
    assert "CAREOPS_PSEUDONYM_KEY" in script
    assert "$select=id,planId,bucketId,createdDateTime,completedDateTime,percentComplete" in script
    unsafe_selection = (
        "$select=id,planId,bucketId,createdDateTime,completedDateTime,percentComplete,title"
    )
    assert unsafe_selection not in script
    assert "tenant_wide_coverage = $null" in script


def test_handling_policy_template_is_fail_closed() -> None:
    """The reusable policy template permits no live content by default."""
    policy = json.loads(
        Path("contracts/corpus-handling-policy.example.json").read_text(encoding="utf-8")
    )
    assert policy["approved_transient_features"] == []
    assert policy["raw_narrative_persistence"] == "prohibited"
    assert policy["direct_identity_persistence"] == "prohibited"
    assert "git_repository" in policy["prohibited_destinations"]


def test_executive_visual_contract_requires_coverage_and_uncertainty() -> None:
    """Executive outputs cannot omit their evidence boundary."""
    contract = json.loads(
        Path("contracts/executive-process-landscape.schema.json").read_text(encoding="utf-8")
    )
    required = set(contract["required"])
    assert required >= {
        "observation_start",
        "observation_end",
        "accessible_denominator",
        "included_population",
        "exclusions",
        "generated_at",
        "tenant_wide_coverage",
    }
    family = contract["properties"]["families"]["items"]
    assert set(family["required"]) >= {
        "confidence",
        "temporal_stability",
        "source_dependence",
        "validation_status",
        "suppressed",
    }
    assert "person_id" not in family["properties"]
    assert "patterns" in required


def test_standalone_renderer_preserves_boundary_and_no_automation_warning() -> None:
    """The no-Fabric fallback remains coverage-honest and governance-safe."""
    script = Path("scripts/build-executive-landscape.py").read_text(encoding="utf-8")
    assert "Partial authorised corpus" in script
    assert "not tenant-wide" in script
    assert "No individual productivity scoring" in script
    assert "No automated workflow changes" in script
    assert "Directly-follows patterns" in script
    assert "Cross-source hand-offs" in script
    assert "Incomplete objects" in script
    assert "Evidence and governance layers" in script
    assert "Escalation events" in script
    assert "Potential bottleneck indicator" in script
