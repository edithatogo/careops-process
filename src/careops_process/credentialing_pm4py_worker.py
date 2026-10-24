# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Isolated optional backend worker; no identifiers, raw alignments or narrative IPC."""

from __future__ import annotations

import importlib
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


def _evaluate(request: dict[str, Any]) -> dict[str, Any]:
    try:
        installed = version("pm4py")
    except PackageNotFoundError:
        return {"status": "version_mismatch"}
    if installed != "2.7.23.8":
        return {"status": "version_mismatch"}
    pm4py = importlib.import_module("pm4py")
    objects = importlib.import_module("pm4py.objects.petri_net.obj")
    utils = importlib.import_module("pm4py.objects.petri_net.utils.petri_utils")
    logs = importlib.import_module("pm4py.objects.log.obj")
    net = objects.PetriNet("bound-canonical-model")
    places = {identity: objects.PetriNet.Place(identity) for identity in request["places"]}
    transitions = {
        identity: objects.PetriNet.Transition(identity, label)
        for identity, label in request["transitions"]
    }
    net.places.update(places.values())
    net.transitions.update(transitions.values())
    nodes = {**places, **transitions}
    for source, target, weight in request["arcs"]:
        utils.add_arc_from_to(nodes[source], nodes[target], net, weight=weight)
    initial = objects.Marking({places[p]: n for p, n in request["initial"]})
    final = objects.Marking({places[p]: n for p, n in request["final"]})
    diagnostics: list[dict[str, Any]] = []
    for trace in request["traces"]:
        log = logs.EventLog([logs.Trace([logs.Event({"concept:name": label}) for label in trace])])
        diagnostics.extend(
            pm4py.conformance_diagnostics_alignments(
                log,
                net,
                initial,
                final,
                multi_processing=False,
                variant_str="Variants.VERSION_DIJKSTRA_SEMANTICS",
                show_progress_bar=False,
                trace_cost_function=[10000] * len(trace),
                model_cost_function={t: 1 if t.label is None else 10000 for t in net.transitions},
                sync_cost_function=dict.fromkeys(net.transitions, 0),
            )
        )
    # Keep the pinned backend's normalization: silent moves cost one but do not
    # reduce visible-move fitness. Raw cost / bwc is not its fitness formula.
    return {
        "status": "available",
        "backend": "2.7.23.8",
        "policy": "pm4py-2.7.23.8-dijkstra-semantics-v1",
        "fitness": [float(item["fitness"]) for item in diagnostics],
        "costs": [int(item["cost"]) for item in diagnostics],
    }


def main() -> None:
    """Read only parent-created bounded input; unexpected failures produce no reply."""
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = _evaluate(request)
    Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    main()
