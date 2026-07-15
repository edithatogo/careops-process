"""Versioned, privacy-preserving OCEL 2.0 contract primitives."""

from __future__ import annotations

import hashlib
import hmac
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

OCEL_VERSION = "2.0"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ContractError(ValueError):
    """Raised when an OCEL contract violates the privacy or identity rules."""


class OcelModel(BaseModel):
    """Base model with no silently accepted extra fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OcelObject(OcelModel):
    """An OCEL object with a stable pseudonymous identity."""

    object_id: str = Field(min_length=1, max_length=128)
    object_type: str = Field(min_length=1, max_length=80)
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("object_id")
    @classmethod
    def safe_id(cls, value: str) -> str:
        """Reject identifiers that could carry uncontrolled content."""
        if not _SAFE_ID.fullmatch(value):
            message = "object_id must be a safe, non-sensitive identifier"
            raise ValueError(message)
        return value


class OcelEvent(OcelModel):
    """An event and its object references."""

    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=120)
    timestamp_utc: datetime
    source_system: str = Field(min_length=1, max_length=80)
    observed_or_inferred: Literal["observed", "inferred"]
    confidence: float = Field(ge=0.0, le=1.0)
    object_ids: list[str] = Field(min_length=1)
    qualifiers: dict[str, str] = Field(default_factory=dict)

    @field_validator("timestamp_utc")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        """Require timezone-aware timestamps and normalize them to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            message = "timestamp_utc must include an explicit timezone"
            raise ValueError(message)
        return value.astimezone(UTC)

    @field_validator("event_id")
    @classmethod
    def safe_event_id(cls, value: str) -> str:
        """Reject uncontrolled event identifiers."""
        if not _SAFE_ID.fullmatch(value):
            message = "event_id must be a safe, non-sensitive identifier"
            raise ValueError(message)
        return value

    @field_validator("object_ids")
    @classmethod
    def safe_object_ids(cls, value: list[str]) -> list[str]:
        """Reject uncontrolled object references."""
        if any(not _SAFE_ID.fullmatch(item) for item in value):
            message = "object_id must be a safe, non-sensitive identifier"
            raise ValueError(message)
        return value


class OcelLog(OcelModel):
    """Minimal OCEL 2.0-compatible envelope for CareOps."""

    ocel_version: Literal["2.0"] = OCEL_VERSION
    log_id: str = Field(min_length=1, max_length=128)
    objects: list[OcelObject] = Field(min_length=1)
    events: list[OcelEvent] = Field(min_length=1)
    lineage: str = Field(min_length=1, max_length=500)
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")


def pseudonymize(value: str, *, secret: str) -> str:
    """Return a deterministic, non-reversible identifier from a local secret."""
    if not secret:
        message = "A non-empty pseudonymization secret is required"
        raise ContractError(message)
    digest = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return "psn_" + digest[:32]


def validate_ocel(log: OcelLog) -> OcelLog:
    """Validate object references and reject direct identity-like attributes."""
    object_ids = {item.object_id for item in log.objects}
    if len(object_ids) != len(log.objects):
        message = "object_id must be unique"
        raise ContractError(message)
    event_ids = {item.event_id for item in log.events}
    if len(event_ids) != len(log.events):
        message = "event_id must be unique"
        raise ContractError(message)
    forbidden = {"email", "email_address", "display_name", "subject", "body", "phone"}
    for item in log.objects:
        if forbidden.intersection(key.lower() for key in item.attributes):
            message = "Direct identity or message-content attributes are prohibited"
            raise ContractError(message)
    for event in log.events:
        if forbidden.intersection(key.lower() for key in event.qualifiers):
            message = "Direct identity or message-content qualifiers are prohibited"
            raise ContractError(message)
        if not set(event.object_ids).issubset(object_ids):
            message = f"Unknown object reference in {event.event_id}"
            raise ContractError(message)
    return log
