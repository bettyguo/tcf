"""End-to-end test for the Phase 3 foundation pipeline.

Proves the foundation slice composes correctly:

    FixtureSource → CEFR classifier → CE synthesizer → quality gate
                                                        ↓
                                              loader → InMemoryBankWriter
                                                        ↓
                                              report_io → JSON on disk

with no LLM call, no real model weights, no network. This is the
"smallest run that exercises the full DAG shape" baseline that the
real Phase 3 implementation must continue to pass.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tcf_accel.schemas import Item, Speaker
from tcf_accel_content.cefr.classify import FakeCEFRClassifier
from tcf_accel_content.load import InMemoryBankWriter, load_candidate
from tcf_accel_content.quality.gate import phase3_foundation_checks, run_gate
from tcf_accel_content.quality.report_io import read_report, write_report
from tcf_accel_content.sources import license_compatible
from tcf_accel_content.sources.fixture import FixtureSource
from tcf_accel_content.synthesize.ce import CESynthesisInput, synthesize_ce_item
from tcf_accel_content.synthesize.co import COSynthesisInput, synthesize_co_item
from tcf_accel_content.synthesize.ee import EESynthesisInput, synthesize_ee_prompt
from tcf_accel_content.synthesize.eo import EOSynthesisInput, synthesize_eo_prompt

_PASSAGES: tuple[str, ...] = (
    "Marie se lève tôt et prend son café avant de partir au travail. "
    "Elle marche jusqu'à la station de métro, lit un livre, et arrive "
    "au bureau à neuf heures. Sa journée commence dans le calme.",
    "Le marché du samedi matin attire toutes les familles du quartier. "
    "On y trouve des fruits frais, du pain artisanal, et des fleurs. "
    "Les enfants jouent pendant que les parents discutent avec les vendeurs.",
    "L'hiver canadien impose une discipline particulière aux nouveaux arrivants. "
    "Il faut prévoir des vêtements adaptés, planifier ses déplacements, "
    "et accepter que certaines journées soient très courtes.",
)


def _write_fixture_manifest(tmp_path: Path) -> Path:
    """Write a small CC-BY-SA-4.0 manifest under tmp_path; return its path."""
    manifest = tmp_path / "manifest.jsonl"
    lines = []
    for idx, passage in enumerate(_PASSAGES, start=1):
        record = {
            "kind": "text",
            "source": "fixture_fr",
            "source_id": f"passage-{idx}",
            "license": "CC-BY-SA-4.0",
            "fetched_at": "2026-05-27T00:00:00+00:00",
            "text": passage,
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def test_foundation_pipeline_produces_passing_items(tmp_path: Path) -> None:
    """Source → classify → synthesize → gate → all three items pass."""
    manifest = _write_fixture_manifest(tmp_path)
    source = FixtureSource(
        name="fixture_fr",
        license="CC-BY-SA-4.0",
        redistributable=True,
        manifest_path=manifest,
    )
    classifier = FakeCEFRClassifier()

    accepted: list[Item] = []
    for asset in source.iter_assets():
        assert asset.text is not None
        assert license_compatible(asset.license)
        candidate = synthesize_ce_item(
            CESynthesisInput(
                passage=asset.text,
                genre="narrative",
                source=asset.source,
                source_id=asset.source_id,
                license=asset.license,
                ingested_at=asset.fetched_at,
                seed=42,
            ),
            classifier=classifier,
        )
        report = run_gate(candidate.item, phase3_foundation_checks())
        assert report.verdict == "pass", (
            f"item {asset.source_id} did not pass the foundation gate: "
            f"{[c for c in report.checks if not c.passed]}"
        )
        accepted.append(candidate.item)

    assert len(accepted) == len(_PASSAGES)
    # All accepted items have distinct ids — the loader's ON CONFLICT
    # contract relies on this.
    assert len({i.id for i in accepted}) == len(accepted)


def test_foundation_pipeline_rejects_non_allowlisted_license(tmp_path: Path) -> None:
    """A passage from an operator-tier source is rejected at the gate."""
    manifest = tmp_path / "bad.jsonl"
    manifest.write_text(
        json.dumps({
            "kind": "text",
            "source": "rfi",
            "source_id": "ep-1",
            "license": "RFI-TOS-personal-study",
            "fetched_at": "2026-05-27T00:00:00+00:00",
            "text": _PASSAGES[0],
        }) + "\n",
        encoding="utf-8",
    )
    source = FixtureSource(
        name="rfi",
        license="RFI-TOS-personal-study",
        redistributable=False,
        manifest_path=manifest,
    )
    asset = next(source.iter_assets())
    candidate = synthesize_ce_item(
        CESynthesisInput(
            passage=asset.text or "",
            genre="news",
            source=asset.source,
            source_id=asset.source_id,
            license=asset.license,
            ingested_at=asset.fetched_at,
            seed=0,
        ),
        classifier=FakeCEFRClassifier(),
    )
    report = run_gate(candidate.item, phase3_foundation_checks())
    assert report.verdict == "reject"
    rejecting = [c for c in report.checks if not c.passed and c.severity == "P0"]
    assert any(c.name == "license_compatible" for c in rejecting)


def test_foundation_pipeline_is_idempotent_across_reruns(tmp_path: Path) -> None:
    """Same inputs → same Item.id; loader's ON CONFLICT DO NOTHING is safe."""
    manifest = _write_fixture_manifest(tmp_path)
    source = FixtureSource(
        name="fixture_fr",
        license="CC-BY-SA-4.0",
        redistributable=True,
        manifest_path=manifest,
    )
    classifier = FakeCEFRClassifier()

    def _run() -> list[str]:
        ids = []
        for asset in source.iter_assets():
            assert asset.text is not None
            candidate = synthesize_ce_item(
                CESynthesisInput(
                    passage=asset.text,
                    genre="narrative",
                    source=asset.source,
                    source_id=asset.source_id,
                    license=asset.license,
                    ingested_at=asset.fetched_at,
                    seed=42,
                ),
                classifier=classifier,
            )
            ids.append(str(candidate.item.id))
        return ids

    assert _run() == _run()


def test_foundation_pipeline_drives_loader_to_persisted_state(tmp_path: Path) -> None:
    """Full DAG: source → synth → gate → loader writes; reports cached to disk."""
    manifest = _write_fixture_manifest(tmp_path)
    source = FixtureSource(
        name="fixture_fr",
        license="CC-BY-SA-4.0",
        redistributable=True,
        manifest_path=manifest,
    )
    classifier = FakeCEFRClassifier()
    writer = InMemoryBankWriter()
    cache_dir = tmp_path / "cache" / "quality"

    outcomes = []
    for asset in source.iter_assets():
        assert asset.text is not None
        candidate = synthesize_ce_item(
            CESynthesisInput(
                passage=asset.text,
                genre="narrative",
                source=asset.source,
                source_id=asset.source_id,
                license=asset.license,
                ingested_at=asset.fetched_at,
                seed=42,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(
            candidate, writer, checks=phase3_foundation_checks(),
        )
        # Audit-trail contract: every gate report lands on disk regardless
        # of verdict, so a later audit can reconstruct decisions.
        write_report(outcome.report, cache_dir / f"{outcome.report.item_id}.json")
        outcomes.append(outcome)

    # All three passages persisted, all reports cached.
    assert all(o.persisted for o in outcomes)
    assert all(o.reason == "wrote" for o in outcomes)
    assert writer.count() == len(_PASSAGES)
    assert len(list(cache_dir.glob("*.json"))) == len(_PASSAGES)

    # Re-running the pipeline produces no new rows (idempotent via the
    # deterministic Item.id contract; phase3_design.md §1.2).
    for asset in source.iter_assets():
        assert asset.text is not None
        candidate = synthesize_ce_item(
            CESynthesisInput(
                passage=asset.text, genre="narrative",
                source=asset.source, source_id=asset.source_id,
                license=asset.license, ingested_at=asset.fetched_at,
                seed=42,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(
            candidate, writer, checks=phase3_foundation_checks(),
        )
        assert outcome.reason == "already_present"

    assert writer.count() == len(_PASSAGES)


def test_foundation_pipeline_persisted_reports_round_trip(tmp_path: Path) -> None:
    """A cached report deserialises back to an equal `QualityReport`."""
    manifest = _write_fixture_manifest(tmp_path)
    source = FixtureSource(
        name="fixture_fr", license="CC-BY-SA-4.0",
        redistributable=True, manifest_path=manifest,
    )
    classifier = FakeCEFRClassifier()
    cache_dir = tmp_path / "cache" / "quality"

    asset = next(source.iter_assets())
    assert asset.text is not None
    candidate = synthesize_ce_item(
        CESynthesisInput(
            passage=asset.text, genre="narrative",
            source=asset.source, source_id=asset.source_id,
            license=asset.license, ingested_at=asset.fetched_at,
            seed=0,
        ),
        classifier=classifier,
    )
    outcome = load_candidate(
        candidate, InMemoryBankWriter(), checks=phase3_foundation_checks(),
    )
    report_path = cache_dir / f"{outcome.report.item_id}.json"
    write_report(outcome.report, report_path)

    recovered = read_report(report_path)
    assert recovered == outcome.report


def test_foundation_pipeline_handles_all_four_modules(tmp_path: Path) -> None:
    """A single bank-build run produces CE + CO + EE + EO items that all
    land in the writer with `wrote` outcome and re-runs are idempotent.
    """
    classifier = FakeCEFRClassifier()
    writer = InMemoryBankWriter()
    checks = phase3_foundation_checks()

    ce_manifest = _write_fixture_manifest(tmp_path)
    ce_source = FixtureSource(
        name="fixture_fr", license="CC-BY-SA-4.0",
        redistributable=True, manifest_path=ce_manifest,
    )

    # CE: one item per fixture passage.
    ce_count = 0
    for asset in ce_source.iter_assets():
        assert asset.text is not None
        cand = synthesize_ce_item(
            CESynthesisInput(
                passage=asset.text, genre="narrative",
                source=asset.source, source_id=asset.source_id,
                license=asset.license, ingested_at=asset.fetched_at,
                seed=42,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(cand, writer, checks=checks)
        assert outcome.reason == "wrote", outcome
        ce_count += 1

    # CO: two clips, different accents, with full acoustic features
    # populated so the audit can see metadata.co_acoustic.
    co_inputs = [
        COSynthesisInput(
            transcript=(
                "Bonjour, je m'appelle Marc. Je travaille comme ingénieur "
                "depuis huit ans à Montréal."
            ),
            audio_local_path="data/cache/audio/co-1.wav",
            duration_s=18.0, accent="fr-CA", register="standard",
            source="common_voice_fr_v17", source_id="co-1",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            speakers=(Speaker(label="Marc", accent="fr-CA"),),
            speech_rate_wpm=140.0, lexical_density=0.55,
            n_speakers_diarized=1, noisiness_proxy=0.10,
            seed=1,
        ),
        COSynthesisInput(
            transcript=(
                "Mesdames et messieurs, je vous souhaite la bienvenue à "
                "cette conférence sur les enjeux climatiques actuels."
            ),
            audio_local_path="data/cache/audio/co-2.wav",
            duration_s=32.5, accent="fr-FR", register="soutenu",
            source="voxpopuli_fr_v2", source_id="co-2",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            speakers=(Speaker(label="Présidente", accent="fr-FR"),),
            speech_rate_wpm=130.0, lexical_density=0.68,
            n_speakers_diarized=1, noisiness_proxy=0.05,
            seed=2,
        ),
    ]
    co_count = 0
    for co_inp in co_inputs:
        cand = synthesize_co_item(co_inp, classifier=classifier)
        outcome = load_candidate(cand, writer, checks=checks)
        assert outcome.reason == "wrote", outcome
        co_count += 1

    # EE: T2 and T3 (both Canadian-context-required), one each.
    for task in (2, 3):
        cand_ee = synthesize_ee_prompt(
            EESynthesisInput(
                task_number=task,  # type: ignore[arg-type]
                canadian_context=True,
                cefr_target="C1",
                seed=task,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(cand_ee, writer, checks=checks)
        assert outcome.reason == "wrote", outcome

    # EO: T1 (no prep) and T3 (argue + defend).
    for task in (1, 3):
        cand_eo = synthesize_eo_prompt(
            EOSynthesisInput(
                task_number=task,  # type: ignore[arg-type]
                cefr_target="C1",
                seed=task,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(cand_eo, writer, checks=checks)
        assert outcome.reason == "wrote", outcome

    expected_total = ce_count + co_count + 2 + 2
    assert writer.count() == expected_total

    # All four modules represented.
    modules = {item.module for item in writer.all_items()}
    assert modules == {"CE", "CO", "EE", "EO"}, modules

    # Re-running every synthesizer with the same seeds produces no new rows.
    for asset in ce_source.iter_assets():
        assert asset.text is not None
        cand = synthesize_ce_item(
            CESynthesisInput(
                passage=asset.text, genre="narrative",
                source=asset.source, source_id=asset.source_id,
                license=asset.license, ingested_at=asset.fetched_at,
                seed=42,
            ),
            classifier=classifier,
        )
        assert load_candidate(cand, writer, checks=checks).reason == "already_present"
    for co_inp in co_inputs:
        cand = synthesize_co_item(co_inp, classifier=classifier)
        assert load_candidate(cand, writer, checks=checks).reason == "already_present"
    for task in (2, 3):
        cand_ee = synthesize_ee_prompt(
            EESynthesisInput(
                task_number=task,  # type: ignore[arg-type]
                canadian_context=True, cefr_target="C1", seed=task,
            ),
            classifier=classifier,
        )
        assert load_candidate(cand_ee, writer, checks=checks).reason == "already_present"
    for task in (1, 3):
        cand_eo = synthesize_eo_prompt(
            EOSynthesisInput(
                task_number=task,  # type: ignore[arg-type]
                cefr_target="C1", seed=task,
            ),
            classifier=classifier,
        )
        assert load_candidate(cand_eo, writer, checks=checks).reason == "already_present"

    assert writer.count() == expected_total


@pytest.mark.parametrize("seed", [0, 1, 7, 42, 1_000_000])
def test_foundation_pipeline_passes_gate_across_seeds(seed: int, tmp_path: Path) -> None:
    """The synthesizer's option-shuffle is gate-safe at any seed."""
    asset_text = _PASSAGES[0]
    candidate = synthesize_ce_item(
        CESynthesisInput(
            passage=asset_text,
            genre="narrative",
            source="fixture_fr",
            source_id="passage-1",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 27, tzinfo=UTC),
            seed=seed,
        ),
        classifier=FakeCEFRClassifier(),
    )
    report = run_gate(candidate.item, phase3_foundation_checks())
    assert report.verdict == "pass"
