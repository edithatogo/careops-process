"""Cloud-only historical backfill contract tests."""

import json
from pathlib import Path
from typing import Any

import pytest

from careops_process.backfill_contract import validate_backfill_contract


def load_contract() -> dict[str, Any]:
    """Load the cloud-only backfill contract."""
    return json.loads(Path("contracts/power-automate-outlook-historical-backfill.json").read_text())


def test_backfill_contract_is_complete_and_privacy_safe() -> None:
    """The shipped contract passes completeness and privacy gates."""
    validate_backfill_contract(load_contract())


def test_backfill_contract_rejects_date_filter() -> None:
    """A convenience date filter cannot masquerade as a full backfill."""
    contract = load_contract()
    contract["completeness_contract"]["date_filter"] = "2026-01-01"
    with pytest.raises(ValueError, match="date filter"):
        validate_backfill_contract(contract)


def test_backfill_contract_rejects_raw_payload_storage() -> None:
    """Raw payload persistence is rejected."""
    contract = load_contract()
    contract["operation"]["never_store_raw_payload"] = False
    with pytest.raises(ValueError, match="raw payload"):
        validate_backfill_contract(contract)


@pytest.mark.parametrize("field", ["from", "sender", "to", "cc", "bcc", "displayName", "phone"])
def test_contract_cannot_drop_identity_privacy_prohibitions(field: str) -> None:
    """Address and identity prohibitions are enforced, not merely declared."""
    contract = load_contract()
    contract["projection"]["forbidden_persistent_fields"].remove(field)
    with pytest.raises(ValueError, match="raw email fields"):
        validate_backfill_contract(contract)


@pytest.mark.parametrize("field", ["id", "internetMessageId", "conversationId", "folder_id"])
def test_contract_requires_all_pseudonym_domains(field: str) -> None:
    """No source identity domain may silently become persistent raw metadata."""
    contract = load_contract()
    contract["projection"]["pseudonymise"].remove(field)
    with pytest.raises(ValueError, match="pseudonym"):
        validate_backfill_contract(contract)


def test_contract_cannot_request_raw_narrative_metadata() -> None:
    """The allowlisted source selection cannot be extended to raw email narrative."""
    contract = load_contract()
    contract["projection"]["allowed_source_metadata"].append("subject")
    with pytest.raises(ValueError, match="source metadata"):
        validate_backfill_contract(contract)
