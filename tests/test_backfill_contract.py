# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

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
