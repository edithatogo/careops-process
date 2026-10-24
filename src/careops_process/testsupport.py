# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic fixtures shared by projection tests."""

from datetime import UTC, datetime

from .ocel import OcelEvent, OcelLog, OcelObject, validate_ocel


def sample_ocel_log() -> OcelLog:
    """Return one synthetic event and its request object."""
    return validate_ocel(
        OcelLog(
            log_id="log-projection",
            schema_version="1.0.0",
            lineage="synthetic projection fixture",
            objects=[OcelObject(object_id="request-1", object_type="approval_request")],
            events=[
                OcelEvent(
                    event_id="event-1",
                    event_type="request_received",
                    timestamp_utc=datetime(2026, 1, 1, tzinfo=UTC),
                    source_system="synthetic",
                    observed_or_inferred="observed",
                    confidence=1.0,
                    object_ids=["request-1"],
                )
            ],
        )
    )
