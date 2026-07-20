"""Build a privacy-screened standalone executive landscape from a local corpus."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from careops_process.correlation import build_ocel_from_facts
from careops_process.coverage import EvidenceClass
from careops_process.executive import EvidenceBoundary, build_executive_landscape
from careops_process.landscape import discover_process_landscape, summarize_operational_patterns


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--observation-start", required=True)
    parser.add_argument("--observation-end", required=True)
    parser.add_argument("--accessible-denominator", required=True, type=int)
    parser.add_argument("--included-population", required=True, type=int)
    parser.add_argument("--exclusion", action="append", default=[])
    parser.add_argument("--small-cell-threshold", type=int, default=5)
    return parser.parse_args()


def _render(payload: dict[str, object], *, title: str) -> str:
    boundary = cast("dict[str, object]", payload["boundary"])
    families = cast("list[dict[str, object]]", payload["families"])
    patterns = cast("dict[str, object]", payload["patterns"])
    cards: list[str] = []
    for family in families:
        if family["suppressed"]:
            detail = "Small-cell detail suppressed"
        else:
            sequence = " → ".join(cast("list[str]", family["activity_sequence"]))
            detail = (
                f"{family['member_count']} objects · {family['event_count']} events<br>"
                f"<code>{html.escape(sequence)}</code>"
            )
        cards.append(
            "<section class='card'>"
            f"<h2>{html.escape(str(family['family_id']))}</h2>"
            f"<p>{detail}</p>"
            f"<p>Confidence {float(family['confidence']):.2f} · "
            f"Stability {float(family['temporal_stability']):.2f} · "
            f"Source dependence {float(family['source_dependence']):.2f}</p>"
            "<p>Evidence layer: inferred family hypothesis</p>"
            f"<p>Status: {html.escape(str(family['validation_status']))}</p>"
            "</section>"
        )
    exclusions = "".join(
        f"<li>{html.escape(str(item))}</li>"
        for item in cast("list[object]", boundary["exclusions"])
    )
    follows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item['from']))}</td>"
        f"<td>{html.escape(str(item['to']))}</td>"
        f"<td>{html.escape(str(item['count']))}</td></tr>"
        for item in cast("list[dict[str, object]]", patterns["directly_follows"])
    )
    handoffs = "".join(
        "<tr>"
        f"<td>{html.escape(str(item['from']))}</td>"
        f"<td>{html.escape(str(item['to']))}</td>"
        f"<td>{html.escape(str(item['count']))}</td></tr>"
        for item in cast("list[dict[str, object]]", patterns["source_handoffs"])
    )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font:16px Segoe UI,Arial,sans-serif;margin:2rem;color:#17324d;background:#f7fafc}}
.warning{{background:#fff2cc;border-left:6px solid #a77b00;padding:1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}}
.card{{background:white;border:1px solid #bdd3df;border-radius:10px;padding:1rem}}
code{{white-space:normal}} small{{color:#526b7a}}
</style><body><h1>{html.escape(title)}</h1>
<div class="warning"><strong>Partial authorised corpus — not tenant-wide.</strong><br>
Observation: {boundary["observation_start"]} to {boundary["observation_end"]} ·
Included population: {boundary["included_population"]} of accessible denominator
{boundary["accessible_denominator"]} · Generated: {boundary["generated_at"]}</div>
<h2>Known exclusions</h2><ul>{exclusions}</ul>
<h2>Unvalidated empirical families</h2><div class="grid">{"".join(cards)}</div>
<h2>Evidence and governance layers</h2>
<ul><li>Observed facts: source lifecycle events</li>
<li>Inferred hypotheses: unvalidated family groupings shown above</li>
<li>Owner-validated processes: none in this partial run</li>
<li>Proposed improvements: none; governance decision required after validation</li></ul>
<h2>Directly-follows patterns</h2>
<table><tr><th>From</th><th>To</th><th>Count</th></tr>{follows}</table>
<h2>Cross-source hand-offs</h2>
<table><tr><th>From</th><th>To</th><th>Count</th></tr>{handoffs}</table>
<h2>Lifecycle indicators</h2>
<p>Rework/loop indicator — repeated adjacent activities: {patterns["repeated_activity_count"]} ·
Escalation events: {patterns["escalation_event_count"]} ·
Incomplete objects: {patterns["incomplete_object_count"]} ·
Potential bottleneck indicator — maximum observed object duration (hours):
{patterns["maximum_duration_hours"]}</p>
<small>No individual productivity scoring. No automated workflow changes.</small></body></html>"""


def main() -> int:
    """Read a local minimized corpus and write aggregate HTML only."""
    args = _arguments()
    source = cast("dict[str, object]", json.loads(args.input.read_text(encoding="utf-8-sig")))
    facts = cast("list[dict[str, object]]", source["facts"])
    log = build_ocel_from_facts(facts, log_id="executive-local", lineage="local run manifest")
    landscape = discover_process_landscape(log)
    patterns = summarize_operational_patterns(log)
    boundary = EvidenceBoundary(
        evidence_class=EvidenceClass.LIVE_CORPUS,
        observation_start=datetime.fromisoformat(args.observation_start),
        observation_end=datetime.fromisoformat(args.observation_end),
        accessible_denominator=args.accessible_denominator,
        included_population=args.included_population,
        exclusions=tuple(args.exclusion),
        generated_at=datetime.now().astimezone(),
    )
    output = build_executive_landscape(
        landscape,
        boundary,
        small_cell_threshold=args.small_cell_threshold,
    )
    payload = {
        "boundary": {
            "evidence_class": output.boundary.evidence_class.value,
            "observation_start": output.boundary.observation_start.isoformat(),
            "observation_end": output.boundary.observation_end.isoformat(),
            "accessible_denominator": output.boundary.accessible_denominator,
            "included_population": output.boundary.included_population,
            "exclusions": list(output.boundary.exclusions),
            "generated_at": output.boundary.generated_at.isoformat(),
        },
        "tenant_wide_coverage": None,
        "families": [
            {
                "family_id": family.family_id,
                "member_count": family.member_count,
                "event_count": family.event_count,
                "activity_sequence": list(family.activity_sequence),
                "confidence": family.confidence,
                "temporal_stability": family.temporal_stability,
                "source_dependence": family.source_dependence,
                "validation_status": family.validation_status,
                "suppressed": family.suppressed,
            }
            for family in output.families
        ],
        "patterns": {
            "directly_follows": [
                {
                    "from": left,
                    "to": right,
                    "count": count if count >= args.small_cell_threshold else "suppressed",
                }
                for left, right, count in patterns.directly_follows
            ],
            "source_handoffs": [
                {
                    "from": left,
                    "to": right,
                    "count": count if count >= args.small_cell_threshold else "suppressed",
                }
                for left, right, count in patterns.source_handoffs
            ],
            "repeated_activity_count": patterns.repeated_activity_count,
            "escalation_event_count": sum(
                "escalat" in event.event_type.lower() for event in log.events
            ),
            "incomplete_object_count": patterns.incomplete_object_count,
            "maximum_duration_hours": round(
                max(patterns.object_duration_seconds, default=0.0) / 3600,
                2,
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        _render(payload, title="IHG process landscape — partial evidence"),
        encoding="utf-8",
    )
    sys.stdout.write(
        json.dumps({"output": str(args.output), "families": len(output.families)}) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
