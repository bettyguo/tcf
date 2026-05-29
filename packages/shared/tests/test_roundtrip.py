"""Property-based round-trip tests (Hypothesis).

For both `Item` and `Score`, a randomly-constructed valid instance should
serialize → deserialize → equal-compare cleanly. Catches subtle schema
bugs (e.g., a `datetime` that loses tzinfo through JSON, a discriminated
union that fails to route).

Phase 2 expands the strategies to cover all four module content shapes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from hypothesis import given
from hypothesis import strategies as st

from tcf_accel.ids import ItemId
from tcf_accel.schemas.common import Provenance, QualityFlag
from tcf_accel.schemas.content import (
    CEContent,
    COContent,
    EEContent,
    EOContent,
    MCQ,
    MCQOption,
    Speaker,
)
from tcf_accel.schemas.item import Item
from tcf_accel.schemas.scoring import Score

_CEFRS = ["A1", "A2", "B1", "B2", "C1", "C2"]
_LICENSES = ["CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT", "proprietary"]
_ACCENTS = ["fr-FR", "fr-CA", "fr-BE", "fr-CH", "fr-AF", "mixed"]
_REGISTERS = ["soutenu", "standard", "familier"]
_GENRES = ["news", "ad", "letter", "admin", "academic", "narrative"]


@st.composite
def _provenance(draw: st.DrawFn) -> Provenance:
    return Provenance(
        source=draw(st.text(min_size=1, max_size=64)),
        source_id=draw(st.text(min_size=1, max_size=64)),
        license=draw(st.sampled_from(_LICENSES)),
        ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
        + timedelta(seconds=draw(st.integers(min_value=0, max_value=10_000_000))),
        review_status=draw(
            st.sampled_from(["auto_passed", "human_approved", "human_modified", "rejected"]),
        ),
    )


@st.composite
def _mcq(draw: st.DrawFn) -> MCQ:
    n = draw(st.integers(min_value=2, max_value=4))
    options = [MCQOption(id=f"o{i}", text=f"text {i}") for i in range(n)]
    return MCQ(
        id=draw(st.text(min_size=1, max_size=8)),
        prompt=draw(st.text(min_size=1, max_size=80)),
        options=options,
        correct_option_id=options[draw(st.integers(min_value=0, max_value=n - 1))].id,
    )


@st.composite
def _co_content(draw: st.DrawFn) -> COContent:
    return COContent(
        transcript=draw(st.text(min_size=1, max_size=200)),
        duration_s=draw(st.floats(min_value=1.0, max_value=600.0, allow_nan=False, allow_infinity=False)),
        speakers=[Speaker(label=f"S{i}", accent=draw(st.sampled_from(_ACCENTS))) for i in range(1, 3)],
        accent=draw(st.sampled_from(_ACCENTS)),  # type: ignore[arg-type]
        register=draw(st.sampled_from(_REGISTERS)),  # type: ignore[arg-type]
        questions=[draw(_mcq())],
    )


@st.composite
def _ce_content(draw: st.DrawFn) -> CEContent:
    return CEContent(
        passage=draw(st.text(min_size=20, max_size=400)),
        genre=draw(st.sampled_from(_GENRES)),  # type: ignore[arg-type]
        word_count=draw(st.integers(min_value=20, max_value=2000)),
        questions=[draw(_mcq())],
    )


@st.composite
def _ee_content(draw: st.DrawFn) -> EEContent:
    lo = draw(st.integers(min_value=40, max_value=200))
    hi = lo + draw(st.integers(min_value=10, max_value=200))
    return EEContent(
        task_number=draw(st.sampled_from([1, 2, 3])),  # type: ignore[arg-type]
        prompt=draw(st.text(min_size=1, max_size=200)),
        target_word_count_range=(lo, hi),
        required_canadian_context=draw(st.booleans()),
        rubric_version=f"ee.v{draw(st.integers(min_value=1, max_value=3))}",
    )


@st.composite
def _eo_content(draw: st.DrawFn) -> EOContent:
    return EOContent(
        task_number=draw(st.sampled_from([1, 2, 3])),  # type: ignore[arg-type]
        examiner_prompts=[draw(st.text(min_size=1, max_size=80))],
        candidate_prep_time_s=draw(st.integers(min_value=0, max_value=600)),
        target_duration_s=draw(st.integers(min_value=30, max_value=600)),
        rubric_version=f"eo.v{draw(st.integers(min_value=1, max_value=3))}",
    )


@st.composite
def _item(draw: st.DrawFn) -> Item:
    kind = draw(st.sampled_from(["CO", "CE", "EE", "EO"]))
    if kind == "CO":
        content = draw(_co_content())
    elif kind == "CE":
        content = draw(_ce_content())
    elif kind == "EE":
        content = draw(_ee_content())
    else:
        content = draw(_eo_content())
    return Item(
        id=ItemId(uuid4()),
        module=kind,  # type: ignore[arg-type]
        cefr_level=draw(st.sampled_from(_CEFRS)),  # type: ignore[arg-type]
        content=content,
        provenance=draw(_provenance()),
        quality_flags=draw(
            st.lists(st.sampled_from(list(QualityFlag)), max_size=4, unique=True),
        ),
        synthetic=draw(st.booleans()),
        retired=draw(st.booleans()),
    )


@given(_item())
def test_item_json_roundtrip(item: Item) -> None:
    dumped = item.model_dump_json()
    reparsed = Item.model_validate_json(dumped)
    assert reparsed == item


@given(_item())
def test_item_dict_roundtrip(item: Item) -> None:
    d = item.model_dump(mode="json")
    reparsed = Item.model_validate(d)
    assert reparsed == item


@given(_item())
def test_item_discriminator_consistent(item: Item) -> None:
    # The narrowed union must keep the outer and inner discriminator in sync.
    assert item.module == item.content.module


@st.composite
def _score(draw: st.DrawFn) -> Score:
    ci_low = draw(st.integers(min_value=1, max_value=12))
    ci_high = draw(st.integers(min_value=ci_low, max_value=12))
    nclc = draw(st.integers(min_value=ci_low, max_value=ci_high))
    return Score(
        nclc=nclc,
        raw=draw(st.floats(min_value=0.0, max_value=699.0, allow_nan=False, allow_infinity=False)),
        ci_low=ci_low,
        ci_high=ci_high,
        n_observations=draw(st.integers(min_value=0, max_value=1000)),
        confident=draw(st.booleans()),
    )


@given(_score())
def test_score_json_roundtrip(s: Score) -> None:
    dumped = s.model_dump_json()
    reparsed = Score.model_validate_json(dumped)
    assert reparsed == s


@given(_score())
def test_score_invariants_hold_after_roundtrip(s: Score) -> None:
    assert s.ci_low <= s.nclc <= s.ci_high
