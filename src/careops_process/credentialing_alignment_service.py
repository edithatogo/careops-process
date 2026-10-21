# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Immutable trusted startup configuration for local authenticated alignments."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, fields
from pathlib import Path

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_alignment import AlignmentModel

_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_MAX_SECONDS = 60
_MAX_REVISION = 2**63 - 1


def _code(value: object, limit: int = 128) -> bool:
    return type(value) is str and 1 <= len(value) <= limit and _CODE.fullmatch(value) is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class AlignmentStoreConfig:
    """Service-owned snapshot coverage/model/runtime metadata, never source approval.

    Coverage definition fixes the external temporal inclusion/completion criteria
    for the entire retained ledger revision. No window or completion is inferred
    from event labels. A source owner must accept those criteria and case mappings.
    """

    model: AlignmentModel
    python: Path
    timeout_seconds: float
    coverage_definition_version: str
    ledger_revision: int
    ledger_sha256: str
    complete_case_ids: frozenset[str]

    def __post_init__(self) -> None:
        """Detach nested configuration and reject coercion/subclass bypasses."""
        if type(self.model) is not AlignmentModel:
            msg = "Alignment service requires a concrete model"
            raise CredentialingContractError(msg)
        detached = AlignmentModel(
            **{field.name: getattr(self.model, field.name) for field in fields(AlignmentModel)}
        )
        object.__setattr__(self, "model", detached)
        if type(self.python) is not type(Path()) or not self.python.is_absolute():
            msg = "Alignment service requires an absolute configured runtime path"
            raise CredentialingContractError(msg)
        if (
            type(self.timeout_seconds) not in (int, float)
            or not 0 < self.timeout_seconds <= _MAX_SECONDS
            or not math.isfinite(self.timeout_seconds)
        ):
            msg = "Alignment service timeout must be finite, positive and bounded"
            raise CredentialingContractError(msg)
        if not _code(self.coverage_definition_version, 80):
            msg = "Alignment service requires an explicit temporal coverage definition"
            raise CredentialingContractError(msg)
        if type(self.ledger_revision) is not int or not 0 <= self.ledger_revision <= _MAX_REVISION:
            msg = "Alignment service coverage must bind an exact ledger revision"
            raise CredentialingContractError(msg)
        if (
            type(self.ledger_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.ledger_sha256) is None
        ):
            msg = "Alignment service coverage requires a canonical retained-state digest"
            raise CredentialingContractError(msg)
        if type(self.complete_case_ids) is not frozenset or any(
            not _code(case) for case in self.complete_case_ids
        ):
            msg = "Alignment service completeness requires safe frozen case references"
            raise CredentialingContractError(msg)


def validate_alignment_config(config: AlignmentStoreConfig) -> AlignmentStoreConfig:
    """Reconstruct a concrete service record instead of retaining caller objects."""
    if type(config) is not AlignmentStoreConfig:
        msg = "Expected concrete trusted alignment configuration"
        raise CredentialingContractError(msg)
    return AlignmentStoreConfig(
        **{field.name: getattr(config, field.name) for field in fields(AlignmentStoreConfig)}
    )
