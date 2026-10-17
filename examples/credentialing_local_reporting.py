"""Run synthetic, aggregate-only credentialing local reporting without AI or I/O."""

from __future__ import annotations

import json
from dataclasses import asdict

from careops_process.credentialing_local_reporting import (
    CaseReportingObservation,
    LocalCredentialingReport,
    ReportingDefinition,
    report_local_credentialing,
)


def synthetic_local_report() -> LocalCredentialingReport:
    """Reconcile four distinct cases with repeated trace activities and replay."""
    cases_per_pathway = 2
    definition = ReportingDefinition(
        definition_version="synthetic-v1",
        window_code="2026-Q3",
        pathway_codes=frozenset({"renewal", "temporary"}),
        reason_codes=frozenset({"missing-document", "administrative-review"}),
    )
    records = tuple(
        CaseReportingObservation.model_validate(
            {
                "observation_id": f"obs-{index}",
                "case_id": f"case-{index}",
                "source_system": "synthetic",
                "definition_version": "synthetic-v1",
                "window_code": "2026-Q3",
                "pathway_code": "renewal" if index < cases_per_pathway else "temporary",
                "correction_reasons": ("missing-document",) if index < cases_per_pathway else (),
                "further_information_reasons": (),
                "deferral_reasons": (),
                "exception_reasons": ()
                if index < cases_per_pathway
                else ("administrative-review",),
                "observed_trace": (
                    "request_received",
                    "correction_requested",
                    "correction_received",
                    "correction_requested",
                    "correction_received",
                    "case_completed",
                )
                if index < cases_per_pathway
                else ("request_received", "case_completed"),
                "elapsed_minutes": 60.0,
                "intervals": (
                    {"start_minute": 0.0, "end_minute": 40.0, "state": "queue"},
                    {"start_minute": 40.0, "end_minute": 55.0, "state": "active"},
                    {"start_minute": 55.0, "end_minute": 60.0, "state": "unknown"},
                ),
            }
        )
        for index in range(4)
    )
    return report_local_credentialing(
        (*records, records[0]),
        role="report_reader",
        granted_case_ids=frozenset(f"case-{index}" for index in range(4)),
        definition=definition,
        source_complete=True,
        minimum_case_count=2,
    )


if __name__ == "__main__":
    print(  # noqa: T201 - executable example prints aggregate-only JSON
        json.dumps(
            {
                "evidence_scope": "synthetic-local-only",
                "definition_version": "synthetic-v1",
                "window_code": "2026-Q3",
                "report": asdict(synthetic_local_report()),
            },
            indent=2,
        )
    )
