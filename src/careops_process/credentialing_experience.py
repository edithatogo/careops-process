"""Supplied single-select instruments and privacy-gated aggregate experience evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never, cast

from careops_process.credentialing import CredentialingContractError

if TYPE_CHECKING:
    from collections.abc import Sequence

_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
_DIGEST = re.compile(r"[a-f0-9]{64}")
_INSTANT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
)
_MAX_COUNT = 1_000_000_000
_MINIMUM = 2
_PAIR_SIZE = 2
_COHORT_KEYS = frozenset(
    {
        "source_system",
        "cohort_ref",
        "definition_version",
        "epoch_ref",
        "window_start_utc",
        "window_end_utc",
    }
)
_QUESTION_KEYS = frozenset({"question_code", "scale_kind", "selection_mode", "categories"})
_COUNT_KEYS = frozenset({"question_code", "answered_count", "category_counts"})
_INSTRUMENT_KEYS = frozenset(
    {"kind", "contract_version", "instrument_code", "version", "questions"}
)
_SNAPSHOT_KEYS = frozenset(
    {
        "kind",
        "contract_version",
        "snapshot_ref",
        "source_system",
        "cohort",
        "instrument_code",
        "instrument_version",
        "instrument_digest",
        "distinct_person_aggregation_attested",
        "invited_count",
        "responded_count",
        "questions",
    }
)


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _code(value: object, limit: int = 128) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("Experience metadata requires bounded opaque reference codes")
    return value


def _fingerprint_value(value: object) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        _fail("Experience snapshot requires the exact instrument fingerprint")


def _count(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= _MAX_COUNT:
        _fail("Experience counts must be bounded nonnegative integer persons")
    return value


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        _fail("Distinct-person source attestation must be a strict boolean")
    return value


def _tuple(value: object) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        _fail("Experience records require immutable tuples")
    return cast("tuple[object, ...]", value)


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("Experience windows require timezone-aware instants")
    try:
        return value.astimezone(UTC)
    except OverflowError:
        _fail("Experience window exceeds the supported UTC range")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperienceCohort:
    """An explicitly supplied source cohort definition and frozen observation epoch."""

    source_system: str
    cohort_ref: str
    definition_version: str
    epoch_ref: str
    window_start_utc: datetime
    window_end_utc: datetime

    def __post_init__(self) -> None:
        """Validate bindings without selecting a population or sampling strategy."""
        _code(self.source_system, 80)
        _code(self.cohort_ref)
        _code(self.definition_version, 80)
        _code(self.epoch_ref)
        start, end = _instant(self.window_start_utc), _instant(self.window_end_utc)
        if start >= end:
            _fail("Experience observation window must have increasing bounds")
        object.__setattr__(self, "window_start_utc", start)
        object.__setattr__(self, "window_end_utc", end)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperienceQuestion:
    """Source-defined single-select nominal or ordinal categories; no numerical scores."""

    question_code: str
    scale_kind: str
    selection_mode: str
    categories: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject unsupported scales, multiselect and repeated response categories."""
        _code(self.question_code, 80)
        if self.scale_kind not in ("nominal", "ordinal"):
            _fail("Experience scale must be supplied as nominal or ordinal")
        if self.selection_mode != "single_select":
            _fail("Experience reporting supports single-select instruments only")
        categories = tuple(_code(value, 80) for value in _tuple(self.categories))
        if not categories or len(set(categories)) != len(categories):
            _fail("Experience response categories must be nonempty and distinct")
        object.__setattr__(
            self,
            "categories",
            tuple(sorted(categories)) if self.scale_kind == "nominal" else categories,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperienceInstrument:
    """A frozen supplied instrument definition; not evidence of instrument approval."""

    instrument_code: str
    version: str
    questions: tuple[ExperienceQuestion, ...]
    contract_version: str = "0.1.0"

    def __post_init__(self) -> None:
        """Detach question definitions and require explicit unique question codes."""
        _code(self.instrument_code, 80)
        _code(self.version, 80)
        if self.contract_version != "0.1.0":
            _fail("Unsupported experience contract version")
        questions: list[ExperienceQuestion] = []
        for value in _tuple(self.questions):
            if type(value) is not ExperienceQuestion:
                _fail("Experience instrument requires supplied question definitions")
            questions.append(replace(value))
        if not questions or len({value.question_code for value in questions}) != len(questions):
            _fail("Experience instrument questions must be nonempty and distinct")
        object.__setattr__(
            self, "questions", tuple(sorted(questions, key=lambda item: item.question_code))
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperienceQuestionCounts:
    """Distinct-person counts in mutually exclusive single-select response categories."""

    question_code: str
    answered_count: int
    category_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        """Require exact category reconciliation and strict integer units."""
        _code(self.question_code, 80)
        _count(self.answered_count)
        counts: list[tuple[str, int]] = []
        for row in _tuple(self.category_counts):
            pair = _tuple(row)
            if len(pair) != _PAIR_SIZE:
                _fail("Experience category counts require code/count pairs")
            counts.append((_code(pair[0], 80), _count(pair[1])))
        if (
            not counts
            or len({code for code, _ in counts}) != len(counts)
            or sum(count for _, count in counts) != self.answered_count
        ):
            _fail("Experience category counts must be distinct and reconcile to answered persons")
        object.__setattr__(self, "category_counts", tuple(sorted(counts)))


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperienceSnapshot:
    """One chosen source-produced aggregate snapshot with no respondent or case identifiers."""

    snapshot_ref: str
    source_system: str
    cohort: ExperienceCohort
    instrument_code: str
    instrument_version: str
    instrument_digest: str
    distinct_person_aggregation_attested: bool
    invited_count: int
    responded_count: int
    questions: tuple[ExperienceQuestionCounts, ...]
    contract_version: str = "0.1.0"

    def __post_init__(self) -> None:
        """Detach retained aggregates and reject contradictory population counts."""
        _code(self.snapshot_ref)
        _code(self.source_system, 80)
        _code(self.instrument_code, 80)
        _code(self.instrument_version, 80)
        if self.contract_version != "0.1.0":
            _fail("Unsupported experience contract version")
        _fingerprint_value(self.instrument_digest)
        object.__setattr__(self, "cohort", _cohort(self.cohort))
        if self.source_system != self.cohort.source_system:
            _fail("Experience snapshot source differs from the frozen cohort source")
        _boolean(self.distinct_person_aggregation_attested)
        invited, responded = _count(self.invited_count), _count(self.responded_count)
        if responded > invited:
            _fail("Experience responses cannot exceed invitations")
        questions: list[ExperienceQuestionCounts] = []
        for value in _tuple(self.questions):
            if type(value) is not ExperienceQuestionCounts:
                _fail("Experience snapshot requires explicit question aggregates")
            question = replace(value)
            if question.answered_count > responded:
                _fail("Experience item answers cannot exceed responding persons")
            questions.append(question)
        if not questions or len({value.question_code for value in questions}) != len(questions):
            _fail("Experience snapshot questions must be nonempty and distinct")
        object.__setattr__(
            self, "questions", tuple(sorted(questions, key=lambda item: item.question_code))
        )


def _cohort(value: object) -> ExperienceCohort:
    # replace preserves runtime subclasses; only concrete contracts may be reconstructed.
    if type(value) is not ExperienceCohort:
        _fail("Experience reporting requires a frozen cohort/window binding")
    return replace(value)


def _snapshot(value: object) -> ExperienceSnapshot:
    if type(value) is not ExperienceSnapshot:
        _fail("Experience reporting requires one snapshot, never a summed collection")
    return replace(value)


def _instrument(value: object) -> ExperienceInstrument:
    if type(value) is not ExperienceInstrument:
        _fail("Experience reporting requires a supplied instrument definition")
    return replace(value)


def experience_instrument_payload(instrument: ExperienceInstrument) -> dict[str, object]:
    """Export the exact bounded instrument wire shape after retained-state validation."""
    value = _instrument(instrument)
    return {
        "kind": "experience_instrument",
        "contract_version": value.contract_version,
        "instrument_code": value.instrument_code,
        "version": value.version,
        "questions": [
            {
                "question_code": question.question_code,
                "scale_kind": question.scale_kind,
                "selection_mode": question.selection_mode,
                "categories": list(question.categories),
            }
            for question in value.questions
        ],
    }


def experience_instrument_digest(instrument: ExperienceInstrument) -> str:
    """Fingerprint the complete supplied instrument, preserving ordinal category order."""
    payload = json.dumps(
        experience_instrument_payload(instrument), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def experience_snapshot_payload(snapshot: ExperienceSnapshot) -> dict[str, object]:
    """Export protected source/cohort references and aggregate counts, never person data."""
    value = _snapshot(snapshot)
    bound = value.cohort
    return {
        "kind": "experience_snapshot",
        "contract_version": value.contract_version,
        "snapshot_ref": value.snapshot_ref,
        "source_system": value.source_system,
        "cohort": {
            "source_system": bound.source_system,
            "cohort_ref": bound.cohort_ref,
            "definition_version": bound.definition_version,
            "epoch_ref": bound.epoch_ref,
            "window_start_utc": bound.window_start_utc.isoformat(),
            "window_end_utc": bound.window_end_utc.isoformat(),
        },
        "instrument_code": value.instrument_code,
        "instrument_version": value.instrument_version,
        "instrument_digest": value.instrument_digest,
        "distinct_person_aggregation_attested": value.distinct_person_aggregation_attested,
        "invited_count": value.invited_count,
        "responded_count": value.responded_count,
        "questions": [
            {
                "question_code": item.question_code,
                "answered_count": item.answered_count,
                "category_counts": [list(pair) for pair in item.category_counts],
            }
            for item in value.questions
        ],
    }


def _wire_map(value: object, keys: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail("Experience wire fields do not match the exact contract")
    mapping = cast("Mapping[object, object]", value)
    if frozenset(mapping) != keys:
        _fail("Experience wire fields do not match the exact contract")
    return cast("Mapping[str, object]", mapping)


def _wire_array(value: object) -> tuple[object, ...]:
    if not isinstance(value, list):
        _fail("Experience wire collections must be arrays")
    return tuple(cast("list[object]", value))


def _wire_instant(value: object) -> datetime:
    if not isinstance(value, str) or not _INSTANT.fullmatch(value):
        _fail("Experience wire windows require strict aware RFC3339 instants")
    try:
        return _instant(datetime.fromisoformat(value.replace("z", "+00:00")))
    except ValueError:
        _fail("Experience wire window is not a valid instant")


def parse_experience_instrument(payload: Mapping[str, object]) -> ExperienceInstrument:
    """Parse a strict single-select instrument without question text or numerical scoring."""
    value = _wire_map(payload, _INSTRUMENT_KEYS)
    if value["kind"] != "experience_instrument" or value["contract_version"] != "0.1.0":
        _fail("Unsupported experience instrument envelope")
    questions: list[ExperienceQuestion] = []
    for row in _wire_array(value["questions"]):
        question = _wire_map(row, _QUESTION_KEYS)
        questions.append(
            ExperienceQuestion(
                question_code=_code(question["question_code"], 80),
                scale_kind=_code(question["scale_kind"], 80),
                selection_mode=_code(question["selection_mode"], 80),
                categories=tuple(_code(item, 80) for item in _wire_array(question["categories"])),
            )
        )
    return ExperienceInstrument(
        instrument_code=_code(value["instrument_code"], 80),
        version=_code(value["version"], 80),
        questions=tuple(questions),
    )


def parse_experience_snapshot(payload: Mapping[str, object]) -> ExperienceSnapshot:
    """Parse one exact aggregate snapshot and reject raw respondent fields or comments."""
    value = _wire_map(payload, _SNAPSHOT_KEYS)
    if value["kind"] != "experience_snapshot" or value["contract_version"] != "0.1.0":
        _fail("Unsupported experience snapshot envelope")
    bound = _wire_map(value["cohort"], _COHORT_KEYS)
    questions: list[ExperienceQuestionCounts] = []
    for row in _wire_array(value["questions"]):
        question = _wire_map(row, _COUNT_KEYS)
        pairs: list[tuple[str, int]] = []
        for raw_pair in _wire_array(question["category_counts"]):
            pair = _wire_array(raw_pair)
            if len(pair) != _PAIR_SIZE:
                _fail("Experience wire category counts require code/count pairs")
            pairs.append((_code(pair[0], 80), _count(pair[1])))
        questions.append(
            ExperienceQuestionCounts(
                question_code=_code(question["question_code"], 80),
                answered_count=_count(question["answered_count"]),
                category_counts=tuple(pairs),
            )
        )
    return ExperienceSnapshot(
        snapshot_ref=_code(value["snapshot_ref"]),
        source_system=_code(value["source_system"], 80),
        cohort=ExperienceCohort(
            source_system=_code(bound["source_system"], 80),
            cohort_ref=_code(bound["cohort_ref"]),
            definition_version=_code(bound["definition_version"], 80),
            epoch_ref=_code(bound["epoch_ref"]),
            window_start_utc=_wire_instant(bound["window_start_utc"]),
            window_end_utc=_wire_instant(bound["window_end_utc"]),
        ),
        instrument_code=_code(value["instrument_code"], 80),
        instrument_version=_code(value["instrument_version"], 80),
        instrument_digest=_code(value["instrument_digest"]),
        distinct_person_aggregation_attested=_boolean(
            value["distinct_person_aggregation_attested"]
        ),
        invited_count=_count(value["invited_count"]),
        responded_count=_count(value["responded_count"]),
        questions=tuple(questions),
    )


def merge_experience_snapshots(
    existing: Sequence[ExperienceSnapshot],
    incoming: Sequence[ExperienceSnapshot],
) -> tuple[ExperienceSnapshot, ...]:
    """Deduplicate source/snapshot identity; retain separate snapshots without adding counts."""
    merged: dict[tuple[str, str], ExperienceSnapshot] = {}
    for supplied in (*existing, *incoming):
        value = _snapshot(supplied)
        key = value.source_system, value.snapshot_ref
        if key in merged and merged[key] != value:
            _fail("Conflicting experience snapshot replay")
        merged[key] = value
    return tuple(merged[key] for key in sorted(merged))


@dataclass(frozen=True, slots=True)
class ExperienceQuestionReport:
    """Released single-select category distribution and respondent item missingness."""

    question_code: str
    scale_kind: str
    answered_count: int
    missing_count: int
    category_counts: tuple[tuple[str, int], ...]
    category_rates: tuple[tuple[str, float | None], ...]
    item_response_rate: float | None
    item_missing_rate: float | None


@dataclass(frozen=True, slots=True)
class ExperienceMetrics:
    """Aggregate survey coverage, with no source, cohort, epoch or respondent identifiers."""

    invited_count: int
    responded_count: int
    nonresponded_count: int
    response_rate: float | None
    questions: tuple[ExperienceQuestionReport, ...]


@dataclass(frozen=True, slots=True)
class ExperienceReport:
    """All released aggregates or whole-report suppression, including totals."""

    suppressed: bool
    metrics: ExperienceMetrics | None


def _scope(role: str, grants: object, minimum: object) -> tuple[frozenset[str], int]:
    if role != "report_reader" or not isinstance(grants, AbstractSet):
        _fail("Experience reporting requires a trusted reader and cohort grant set")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < _MINIMUM:
        _fail("Experience privacy threshold requires at least two distinct persons")
    granted = frozenset(_code(value) for value in cast("AbstractSet[object]", grants))
    return granted, minimum


def report_experience(  # noqa: PLR0913 - explicit trusted scope and frozen source definition
    snapshot: ExperienceSnapshot,
    instrument: ExperienceInstrument,
    *,
    role: str,
    granted_cohort_refs: AbstractSet[str],
    minimum_respondents: object,
    expected_cohort: ExperienceCohort,
) -> ExperienceReport:
    """Release one bound source-attested snapshot without local identity deduplication.

    Source owners define the instrument, sampling cohort and distinct-person
    aggregation. Trusted adapters resolve grants and expected definitions. This
    function checks supplied assertions and arithmetic, not their authenticity.
    """
    grants, minimum = _scope(role, granted_cohort_refs, minimum_respondents)
    value, profile, bound = _snapshot(snapshot), _instrument(instrument), _cohort(expected_cohort)
    if value.cohort != bound or value.cohort.cohort_ref not in grants:
        _fail("Experience snapshot does not match the authorized frozen cohort/window")
    if (
        value.instrument_code != profile.instrument_code
        or value.instrument_version != profile.version
        or value.instrument_digest != experience_instrument_digest(profile)
        or {item.question_code for item in value.questions}
        != {item.question_code for item in profile.questions}
    ):
        _fail("Experience snapshot does not match the complete supplied instrument")
    definitions = {item.question_code: item for item in profile.questions}
    reports: list[ExperienceQuestionReport] = []
    cells = [
        value.invited_count,
        value.responded_count,
        value.invited_count - value.responded_count,
    ]
    for question in value.questions:
        definition = definitions[question.question_code]
        counts = dict(question.category_counts)
        if set(counts) != set(definition.categories):
            _fail("Experience snapshot categories do not match the supplied instrument")
        answered, missing = question.answered_count, value.responded_count - question.answered_count
        cells.extend((answered, missing, *counts.values()))
        reports.append(
            ExperienceQuestionReport(
                question.question_code,
                definition.scale_kind,
                answered,
                missing,
                tuple((code, counts[code]) for code in definition.categories),
                tuple(
                    (code, counts[code] / answered if answered else None)
                    for code in definition.categories
                ),
                answered / value.responded_count if value.responded_count else None,
                missing / value.responded_count if value.responded_count else None,
            )
        )
    if (
        not value.distinct_person_aggregation_attested
        or not value.invited_count
        or any(0 < count < minimum for count in cells)
    ):
        return ExperienceReport(suppressed=True, metrics=None)
    return ExperienceReport(
        suppressed=False,
        metrics=ExperienceMetrics(
            value.invited_count,
            value.responded_count,
            value.invited_count - value.responded_count,
            value.responded_count / value.invited_count if value.invited_count else None,
            tuple(reports),
        ),
    )
