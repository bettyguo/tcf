"""Contract-level a11y assertions (`phase5_audit.md §5`).

The full axe-core + Playwright keyboard-walkthrough suite requires the
Phase 8 frontend; it lives there. What we *can* assert in Phase 5,
without a frontend, is that the **drill-side contracts** the
accessibility design depends on are wired correctly:

- CO drills declare `single_play=True` (ADR-029 — no replay during the
  question; the audit anti-criterion).
- Audio-recording EO drills declare `requires_audio_in=True` so the
  Phase 8 UI knows to render a microphone affordance.
- Accessibility alternatives are reachable in the registry under their
  documented names, and emit the right `module` (`co_lexical_alt` →
  `module="CE"`, `eo_text_alt` → `module="EE"`).
- The CO core drill declares its accessibility alternative
  (`accessibility_alt="co_lexical_alt"`) so the route-side swap can
  find it by spec.
- Banner keys for accessibility drills are stable, non-empty strings
  that the UI's banner copy table can look up.

These are *structural* a11y guarantees the route + drill engine
honor; the *rendered* a11y (axe-core scan, keyboard walk) lands when
Phase 8's UI exists.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item
from tcf_accel_sla.drills import (
    REGISTRY,
    COLexicalAltDrill,
    COMCQDrill,
    EOTextAltDrill,
    get_drill,
)

_CO_DRILLS = ("co_mcq", "co_dictation", "co_gapfill")
_EO_AUDIO_DRILLS = ("eo_task", "eo_picture", "eo_spontaneous", "eo_roleplay", "eo_repair")
_ACCESSIBILITY_ALTS = ("co_lexical_alt", "eo_text_alt")


# ─── Single-play contract (ADR-029) ───────────────────────────


@pytest.mark.parametrize("kind", _CO_DRILLS)
def test_co_drills_declare_single_play(kind: str) -> None:
    """The CO core drills enforce the single-play UX contract via DrillSpec."""
    assert get_drill(kind).spec.single_play is True


def test_co_lexical_alt_does_not_inherit_single_play() -> None:
    """The accessibility alt is text-based — no audio, so single-play
    doesn't apply. The spec must reflect that (and the route knows
    not to bind audio controls to a non-audio drill)."""
    assert COLexicalAltDrill().spec.single_play is False


# ─── Audio-input declarations ─────────────────────────────────


@pytest.mark.parametrize("kind", _EO_AUDIO_DRILLS)
def test_eo_drills_declare_audio_in(kind: str) -> None:
    """All EO drills that record the learner declare `requires_audio_in`."""
    assert get_drill(kind).spec.requires_audio_in is True


def test_eo_task_declares_audio_out_for_examiner_tts() -> None:
    """`eo_task` and `eo_roleplay` render examiner TTS prompts → audio_out."""
    assert get_drill("eo_task").spec.requires_audio_out is True
    assert get_drill("eo_roleplay").spec.requires_audio_out is True


def test_eo_text_alt_declares_no_audio_io() -> None:
    """The text-input alternative must not require audio I/O — that's
    the whole point. A future contributor who flips one of these flags
    breaks the accessibility contract."""
    spec = EOTextAltDrill().spec
    assert spec.requires_audio_in is False
    assert spec.requires_audio_out is False


# ─── Accessibility-alt routing wired in DrillSpec ─────────────


def test_co_mcq_declares_its_accessibility_alt() -> None:
    """The route-side swap in `start` finds the alternative by spec;
    the alt name must be reachable from the core drill's DrillSpec."""
    assert COMCQDrill().spec.accessibility_alt == "co_lexical_alt"


def test_accessibility_alts_resolve_in_registry() -> None:
    for kind in _ACCESSIBILITY_ALTS:
        drill = get_drill(kind)
        assert drill.spec.drill_kind == kind


def test_co_lexical_alt_emits_module_ce_not_co() -> None:
    """ADR-029 load-bearing: a CO accessibility drill writes to CE."""
    assert COLexicalAltDrill().spec.module == "CE"


def test_eo_text_alt_emits_module_ee_not_eo() -> None:
    """Symmetric to ADR-029: EO accessibility writes to EE."""
    assert EOTextAltDrill().spec.module == "EE"


# ─── Banner keys for the UI's a11y banner lookup ──────────────


def _eo_item() -> Item:
    return Item(
        id=uuid4(),
        module="EO",
        cefr_level="B2",
        content=EOContent(
            task_number=1,
            examiner_prompts=["Présentez-vous."],
            candidate_prep_time_s=0,
            target_duration_s=180,
            rubric_version="eo.v1",
        ),
        provenance=Provenance(
            source="t",
            source_id="t",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
    )


def test_eo_text_alt_present_carries_banner_key() -> None:
    """The accessibility banner key is required so the UI can look up
    localized banner copy without hard-coding strings into the drill
    or the frontend."""
    step = EOTextAltDrill().present(_eo_item())
    key = step.payload.get("accessibility_banner_key")
    assert isinstance(key, str) and key == "eo_text_alt"


# ─── Registry coverage: every Phase 5 drill is registered ─────


def test_registry_covers_all_phase5_implementable_kinds() -> None:
    """The 14 drill kinds Phase 5 ships must all resolve in the registry.
    `ee_connector` and `ee_error_correction` are deferred (bank-shape
    + Phase 7 dependencies) and not registered yet — they're the
    `NotImplementedError` path tested elsewhere."""
    expected = {
        # CO (incl. accessibility alt)
        "co_mcq",
        "co_dictation",
        "co_gapfill",
        "co_lexical_alt",
        # CE
        "ce_mcq",
        # EE
        "ee_task",
        "ee_rewrite",
        "ee_register_adjust",
        # EO (incl. accessibility alt + repair)
        "eo_task",
        "eo_picture",
        "eo_spontaneous",
        "eo_roleplay",
        "eo_repair",
        "eo_text_alt",
    }
    assert expected.issubset(REGISTRY.keys())


def test_all_registered_drills_have_a_module() -> None:
    """A drill without a `module` would be unscheduable. Pin the invariant."""
    for kind, drill in REGISTRY.items():
        assert drill.spec.module in {"CO", "CE", "EE", "EO"}, kind
