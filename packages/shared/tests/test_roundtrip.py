"""Property-based round-trip tests (Hypothesis).

For both `Item` and `Score`, a randomly-constructed valid instance should
serialize → deserialize → equal-compare cleanly. Catches subtle schema bugs
(e.g., a `datetime` that loses tzinfo through JSON).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from hypothesis import given
from hypothesis import strategies as st

from tcf_accel.ids import ItemId
from tcf_accel.schemas.common import Provenance, QualityFlag
from tcf_accel.schemas.item import Item, ItemContent
from tcf_accel.schemas.scoring import Score

_MODULES = ["CO", "CE", "EE", "EO"]
_CEFRS = ["A1", "A2", "B1", "B2", "C1", "C2"]
_LICENSES = ["CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT", "proprietary"]


@st.composite
def _provenance(draw: st.DrawFn) -> Provenance:
    return Provenance(
        source=draw(st.text(min_size=1, max_size=64)),
        source_id=draw(st.text(min_size=1, max_size=64)),
        license=draw(st.sampled_from(_LICENSES)),
        ingested_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(
            seconds=draw(st.integers(min_value=0, max_value=10_000_000)),
        ),
        review_status=draw(
            st.sampled_from(["auto_passed", "human_approved", "human_modified", "rejected"])
        ),
    )


@st.composite
def _item(draw: st.DrawFn) -> Item:
    module = draw(st.sampled_from(_MODULES))
    return Item(
        id=ItemId(uuid4()),
        module=module,           # type: ignore[arg-type]
        cefr_level=draw(st.sampled_from(_CEFRS)),  # type: ignore[arg-type]
        content=ItemContent(module=module),         # type: ignore[arg-type]
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
    # Defensive: the validator should have run already, but check post-parse too.
    assert s.ci_low <= s.nclc <= s.ci_high
