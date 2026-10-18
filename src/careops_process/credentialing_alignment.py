"""Bounded optional cost-based Petri alignments; no clinical or causal claims."""

from __future__ import annotations

import hashlib
import json
import math
import re

# Trusted configured interpreter and fixed worker; no shell.
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never, cast, get_args

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring

from careops_process.credentialing import Activity, CredentialingContractError

if TYPE_CHECKING:
    from collections.abc import Iterable

    # Type only; actual parsing uses defusedxml.
    from xml.etree.ElementTree import Element  # nosec B405

BACKEND_VERSION = "2.7.23.8"
COST_POLICY = "pm4py-2.7.23.8-default-alignment-v1"
_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_NET_TYPE = "http://www.pnml.org/version-2009/grammar/pnmlcoremodel"
_ACTIVITIES = frozenset(get_args(Activity))
_MAX_MODEL_BYTES = 131072
_MAX_TRACES = 64
_MAX_EVENTS = 128
_MAX_REPLY = 32768
_MAX_NODES = 128
_MAX_ARCS = 512
_PAIR_LENGTH = 2
_MAX_TOKENS = 32
_MAX_COST = 10_000_000
_MAX_SECONDS = 60
_SCHEMA: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "pnml": (frozenset(), frozenset({"net"})),
    "net": (frozenset({"id", "type"}), frozenset({"name", "page"})),
    "page": (frozenset({"id"}), frozenset({"place", "transition", "arc"})),
    "place": (frozenset({"id"}), frozenset({"name"})),
    "transition": (frozenset({"id"}), frozenset({"name"})),
    "arc": (frozenset({"id", "source", "target"}), frozenset({"inscription"})),
    "name": (frozenset(), frozenset({"text"})),
    "inscription": (frozenset(), frozenset({"text"})),
    "text": (frozenset(), frozenset()),
}


def _fail(message: str) -> Never:
    raise CredentialingContractError(message)


def _code(value: object) -> None:
    if type(value) is not str or _CODE.fullmatch(value) is None:
        _fail("Alignment references require bounded concrete codes")


def _text(node: Element, kind: str) -> str | None:
    containers = node.findall(kind)
    if len(containers) > 1 or (containers and len(containers[0]) != 1):
        _fail("PNML text structure is ambiguous")
    return None if not containers else containers[0][0].text


def _pnml(artifact: bytes) -> dict[str, object]:  # noqa: C901, PLR0912 -- Closed PNML subset validation.
    if type(artifact) is not bytes or not 1 <= len(artifact) <= _MAX_MODEL_BYTES:
        _fail("PNML artifact exceeds bounded byte range")
    try:
        root = fromstring(artifact, forbid_dtd=True)
    except SyntaxError, DefusedXmlException:
        _fail("PNML XML is invalid or unsafe")
    if root.tag != "pnml" or len(root) != 1 or root[0].tag != "net":
        _fail("PNML requires exactly one canonical net")
    net = root[0]
    if net.get("type") != _NET_TYPE or len(net.findall("page")) != 1:
        _fail("PNML requires one canonical P/T page")
    for node in root.iter():
        rule = _SCHEMA.get(str(node.tag))
        if (
            rule is None
            or frozenset(node.attrib) != rule[0]
            or any(child.tag not in rule[1] for child in node)
        ):
            _fail("PNML unsupported structure or semantics")
        if (node.text or "").strip() and node.tag != "text":
            _fail("PNML unsupported mixed content")
        if (node.tail or "").strip():
            _fail("PNML unsupported mixed content")
        if "id" in node.attrib:
            _code(node.attrib["id"])
    page = net.find("page")
    if page is None:
        _fail("PNML page is missing")
    places = tuple(node.attrib["id"] for node in page.findall("place"))
    transitions: list[tuple[str, str | None]] = []
    ids = [node.attrib["id"] for node in root.iter() if "id" in node.attrib]
    if len(set(ids)) != len(ids) or not 1 <= len(places) <= _MAX_NODES:
        _fail("PNML identities or place bounds are invalid")
    for node in page.findall("transition"):
        label = _text(node, "name")
        if label is not None and label not in _ACTIVITIES:
            _fail("PNML visible labels must be registered credentialing activities")
        if node.findall("name") and label is None:
            _fail("PNML named transitions require a nonempty activity")
        transitions.append((node.attrib["id"], label))
    if not 1 <= len(transitions) <= _MAX_NODES or not any(label for _, label in transitions):
        _fail("PNML requires bounded transitions and at least one visible activity")
    transition_ids = {identity for identity, _ in transitions}
    arcs: list[tuple[str, str, int]] = []
    for node in page.findall("arc"):
        source, target = node.attrib["source"], node.attrib["target"]
        if not (
            (source in places and target in transition_ids)
            or (source in transition_ids and target in places)
        ):
            _fail("PNML arcs must connect an existing place and transition")
        inscription = _text(node, "inscription")
        if node.findall("inscription") and inscription is None:
            _fail("PNML arc inscription is missing")
        if inscription is not None and not re.fullmatch(r"[1-9][0-9]?", inscription):
            _fail("PNML arc weights require bounded positive integers")
        arcs.append((source, target, 1 if inscription is None else int(inscription)))
    if not 1 <= len(arcs) <= _MAX_ARCS or len({(s, t) for s, t, _ in arcs}) != len(arcs):
        _fail("PNML arc bounds or duplicate edges are invalid")
    return {"places": places, "transitions": transitions, "arcs": arcs}


def _marking(value: object, places: object) -> None:
    if type(value) is not tuple or not value:
        _fail("Alignment marking must be explicit and nonempty")
    seen: set[str] = set()
    for pair in cast("tuple[object, ...]", value):
        if type(pair) is not tuple:
            _fail("Alignment marking requires place/token pairs")
        pair = cast("tuple[object, ...]", pair)
        if len(pair) != _PAIR_LENGTH:
            _fail("Alignment marking requires place/token pairs")
        place_value, tokens = pair
        place = cast("str", place_value)
        _code(place)
        if place not in cast("tuple[str, ...]", places) or place in seen:
            _fail("Alignment marking has unknown or duplicate places")
        if type(tokens) is not int or not 1 <= tokens <= _MAX_TOKENS:
            _fail("Alignment marking requires bounded positive integer tokens")
        seen.add(place)


@dataclass(frozen=True, kw_only=True)
class AlignmentModel:
    """Trusted model binding; constructor checks structure, never clinical approval.

    Canonical PNML has one unnamespaced page, plain weighted P/T arcs, registered
    visible activity names, and unnamed silent transitions. Markings are separate
    explicit bindings; embedded markings/extensions are rejected, never guessed.
    """

    pnml: bytes
    sha256: str
    model_version: str
    pathway_code: str
    authority_version: str
    activity_mapping_version: str
    initial_marking: tuple[tuple[str, int], ...]
    final_marking: tuple[tuple[str, int], ...]
    cost_policy: str = COST_POLICY

    def __post_init__(self) -> None:
        """Pin actual model bytes, scope qualifiers and explicit markings."""
        for value in (
            self.model_version,
            self.pathway_code,
            self.authority_version,
            self.activity_mapping_version,
        ):
            _code(value)
        topology = _pnml(self.pnml)
        if type(self.sha256) is not str or hashlib.sha256(self.pnml).hexdigest() != self.sha256:
            _fail("Alignment model digest mismatch")
        if type(self.cost_policy) is not str or self.cost_policy != COST_POLICY:
            _fail("Alignment cost policy is unsupported")
        _marking(self.initial_marking, topology["places"])
        _marking(self.final_marking, topology["places"])


AlignmentStatus = Literal[
    "available", "runtime_unavailable", "version_mismatch", "resource_limit", "backend_error"
]


@dataclass(frozen=True, slots=True)
class AlignmentResult:
    """Restricted ordered trace diagnostics, not a privacy-safe broad release."""

    status: AlignmentStatus
    fitness: tuple[float, ...] | None = None
    costs: tuple[int, ...] | None = None


def _result(payload: object, count: int) -> AlignmentResult:  # noqa: PLR0911 -- Fail-closed IPC.
    if not isinstance(payload, dict):
        return AlignmentResult("backend_error")
    payload = cast("dict[str, object]", payload)
    if payload == {"status": "version_mismatch"}:
        return AlignmentResult("version_mismatch")
    if set(payload) != {"status", "fitness", "costs", "backend", "policy"} or (
        payload["status"],
        payload["backend"],
        payload["policy"],
    ) != ("available", BACKEND_VERSION, COST_POLICY):
        return AlignmentResult("backend_error")
    fitness_value, costs_value = payload["fitness"], payload["costs"]
    if type(fitness_value) is not list or type(costs_value) is not list:
        return AlignmentResult("backend_error")
    fitness = cast("list[float]", fitness_value)
    costs = cast("list[int]", costs_value)
    if len(fitness) != count or len(costs) != count:
        return AlignmentResult("backend_error")
    if any(type(x) not in (int, float) or not 0 <= x <= 1 or not math.isfinite(x) for x in fitness):
        return AlignmentResult("backend_error")
    if any(type(x) is not int or not 0 <= x <= _MAX_COST for x in costs):
        return AlignmentResult("backend_error")
    return AlignmentResult("available", tuple(float(x) for x in fitness), tuple(costs))


def align_traces(  # noqa: C901, PLR0911 -- Explicit isolated process failure states.
    model: AlignmentModel,
    traces: Iterable[tuple[str, ...]],
    *,
    python: Path,
    timeout_seconds: float = 30,
) -> AlignmentResult:
    """Run pinned backend in a killable child with bounded input/output files.

    Interpreter is trusted server configuration, never a request parameter. This
    is a restricted primitive; trace order/results require case-authorised access.
    Wall-clock/input/output bounds are not an OS memory or CPU quota.
    """
    if type(model) is not AlignmentModel:
        _fail("Alignment requires a concrete bound model")
    model = AlignmentModel(**vars(model))
    retained = tuple(islice(traces, _MAX_TRACES + 1))
    if not 1 <= len(retained) <= _MAX_TRACES:
        return AlignmentResult("resource_limit")
    for trace in retained:
        if type(trace) is not tuple or not 1 <= len(trace) <= _MAX_EVENTS:
            _fail("Alignment requires nonempty bounded complete activity traces")
        if any(type(label) is not str or label not in _ACTIVITIES for label in trace):
            _fail("Alignment traces require concrete registered activity labels")
    if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= _MAX_SECONDS:
        _fail("Alignment timeout must be positive and at most sixty seconds")
    if not python.is_absolute():
        _fail("Alignment interpreter requires an absolute configured path")
    if not python.is_file():
        return AlignmentResult("runtime_unavailable")
    request = {
        **_pnml(model.pnml),
        "initial": model.initial_marking,
        "final": model.final_marking,
        "traces": retained,
    }
    with tempfile.TemporaryDirectory(prefix="careops-alignment-") as folder:
        request_path, reply_path = Path(folder) / "input.json", Path(folder) / "output.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        worker = Path(__file__).with_name("credentialing_pm4py_worker.py")
        try:
            # Trusted service config supplies interpreter; fixed worker, no shell.
            completed = subprocess.run(  # noqa: S603  # nosec B603
                [str(python), "-I", str(worker), str(request_path), str(reply_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return AlignmentResult("resource_limit")
        except OSError:
            return AlignmentResult("runtime_unavailable")
        if (
            completed.returncode != 0
            or not reply_path.is_file()
            or reply_path.stat().st_size > _MAX_REPLY
        ):
            return AlignmentResult("backend_error")
        try:
            return _result(json.loads(reply_path.read_text(encoding="utf-8")), len(retained))
        except ValueError, OSError, RecursionError:
            return AlignmentResult("backend_error")
