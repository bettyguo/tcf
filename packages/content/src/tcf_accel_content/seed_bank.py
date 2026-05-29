"""Foundation seed-bank builder.

`scripts/seed_bank.py` is a thin wrapper over `main` here. The logic
lives in this module so tests can import and call `run_build` and
`main` directly without subprocess overhead.

The foundation impl runs *only* the open-only pipeline shape against
self-contained deterministic seed data:

- CE: a small pool of hand-authored CC-BY-SA-4.0 French passages.
- CO: hardcoded transcript + acoustic metadata stubs (no real audio;
  the foundation impl exercises the synth + gate + loader contract,
  not Phase 5's audio playback).
- EE: parameter-driven; the curated prompt pool in `synthesize.ee`.
- EO: parameter-driven; the curated examiner-script pool in `synthesize.eo`.

When the Phase 3 follow-up lands, this CLI swaps:

1. The self-contained seed data for `tcf_accel_content.sources.*` modules
   (Common Voice, MLS, Voxpopuli, Wikisource, Gutenberg).
2. `FakeCEFRClassifier` for `CamembertCEFRClassifier`.
3. `InMemoryBankWriter` for `PostgresBankWriter`.
4. The foundation MCQ synth for the LLM-driven CE/CO synth + adversarial
   gate.

Operator-facing surface (CLI flags, BankStats output shape) does not
change; this is the contract Phase 3 follow-up must respect.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import TextIO

from tcf_accel.schemas import Item, Speaker

from tcf_accel_content.cefr.classify import FakeCEFRClassifier
from tcf_accel_content.load import InMemoryBankWriter, load_candidate
from tcf_accel_content.quality.gate import phase3_foundation_checks
from tcf_accel_content.synthesize.ce import CESynthesisInput, synthesize_ce_item
from tcf_accel_content.synthesize.co import COSynthesisInput, synthesize_co_item
from tcf_accel_content.synthesize.ee import EESynthesisInput, synthesize_ee_prompt
from tcf_accel_content.synthesize.eo import EOSynthesisInput, synthesize_eo_prompt

# ─── Foundation seed data ──────────────────────────────────────

_CE_PASSAGES: tuple[str, ...] = (
    "Marie se lève tôt et prend son café avant de partir au travail. "
    "Elle marche jusqu'à la station de métro, lit un livre, et arrive "
    "au bureau à neuf heures. Sa journée commence dans le calme.",
    "Le marché du samedi matin attire toutes les familles du quartier. "
    "On y trouve des fruits frais, du pain artisanal, et des fleurs. "
    "Les enfants jouent pendant que les parents discutent.",
    "L'hiver canadien impose une discipline particulière aux nouveaux "
    "arrivants. Il faut prévoir des vêtements adaptés, planifier ses "
    "déplacements, et accepter que certaines journées soient très courtes.",
    "À midi, l'équipe se retrouve dans la salle de pause pour partager "
    "un repas et discuter du projet en cours. Les idées circulent "
    "librement et les décisions importantes se prennent souvent là.",
    "Le bilinguisme au Canada est plus qu'une politique : c'est une "
    "réalité quotidienne dans plusieurs régions. Apprendre les deux "
    "langues officielles ouvre des portes professionnelles et culturelles.",
    "Le télétravail a transformé l'organisation des entreprises. Certains "
    "y voient une libération, d'autres regrettent les échanges informels "
    "qui faisaient la richesse des bureaux traditionnels.",
    "Les transports en commun de Montréal desservent un vaste réseau "
    "métropolitain. Le métro fonctionne tôt le matin jusqu'à tard le "
    "soir, et les autobus complètent les zones moins denses.",
    "La cuisine québécoise s'inspire de traditions françaises et "
    "autochtones tout en intégrant des influences plus récentes. La "
    "poutine, la tourtière et le sirop d'érable en sont des emblèmes.",
)


@dataclass(frozen=True)
class _COSeed:
    """One CO seed entry: enough to feed the foundation synthesizer."""

    transcript: str
    duration_s: float
    accent: str
    register: str
    source: str
    source_id: str
    license: str


_CO_SEEDS: tuple[_COSeed, ...] = (
    _COSeed(
        transcript=(
            "Bonjour, je m'appelle Annick. Je travaille dans une "
            "entreprise de services à Québec depuis trois ans."
        ),
        duration_s=14.0, accent="fr-CA", register="standard",
        source="common_voice_fr_v17", source_id="seed-co-1",
        license="CC0-1.0",
    ),
    _COSeed(
        transcript=(
            "Mesdames et messieurs, je vous remercie de votre présence. "
            "Nous allons examiner les enjeux climatiques de notre époque."
        ),
        duration_s=22.5, accent="fr-FR", register="soutenu",
        source="voxpopuli_fr_v2", source_id="seed-co-2",
        license="CC0-1.0",
    ),
    _COSeed(
        transcript=(
            "Salut tout le monde ! Aujourd'hui on va parler de musique "
            "et de festivals. Vous savez, l'été c'est vraiment génial."
        ),
        duration_s=18.0, accent="fr-CA", register="familier",
        source="common_voice_fr_v17", source_id="seed-co-3",
        license="CC0-1.0",
    ),
    _COSeed(
        transcript=(
            "L'enregistrement suivant présente une discussion entre deux "
            "collègues à propos d'un nouveau projet logiciel à livrer."
        ),
        duration_s=20.0, accent="fr-FR", register="standard",
        source="multilingual_librispeech_fr", source_id="seed-co-4",
        license="CC-BY-4.0",
    ),
)


# ─── Stats ─────────────────────────────────────────────────────


@dataclass
class ModuleStats:
    """Per-module persistence counts."""

    target: int = 0
    persisted: int = 0
    already_present: int = 0
    rejected: int = 0
    flagged_skipped: int = 0


@dataclass
class BankStats:
    """Aggregate result of a seed_bank run; rendered to Markdown by `render`."""

    mode: str
    seed: int
    per_module: dict[str, ModuleStats] = field(default_factory=dict)
    cefr_levels: Counter[str] = field(default_factory=Counter)

    def record(self, module: str, reason: str) -> None:
        """Increment the per-module counter matching `reason`."""
        m = self.per_module.setdefault(module, ModuleStats())
        if reason == "wrote":
            m.persisted += 1
        elif reason == "already_present":
            m.already_present += 1
        elif reason == "rejected_p0":
            m.rejected += 1
        elif reason == "flagged_p1_skipped":
            m.flagged_skipped += 1

    def total_persisted(self) -> int:
        """Sum of `persisted` across all modules in this run."""
        return sum(m.persisted for m in self.per_module.values())


# ─── Build orchestration ───────────────────────────────────────


def run_build(
    *,
    mode: str = "open-only",
    target_ce: int = 8,
    target_co: int = 4,
    target_ee: int = 4,
    target_eo: int = 4,
    seed: int = 0,
    writer: InMemoryBankWriter | None = None,
) -> tuple[BankStats, InMemoryBankWriter]:
    """Run the foundation pipeline; return aggregate stats + the writer.

    Args:
        mode: Only ``"open-only"`` is supported in the foundation impl.
            Phase 3 follow-up adds ``"with-operator-ingest"``.
        target_ce: CE-item target (clamped to the CE seed-pool size).
        target_co: CO-item target (clamped to the CO seed-pool size).
        target_ee: EE-item target (unbounded; pool is parameter-driven).
        target_eo: EO-item target (unbounded; pool is parameter-driven).
        seed: Global synthesis seed; varies the deterministic
            permutations of MCQ options and EE/EO prompt variants.
        writer: Optional pre-existing `InMemoryBankWriter` to write
            into (useful for tests that want to inspect the rows).
            Created fresh when omitted.

    Returns:
        ``(stats, writer)``. The writer carries every persisted item;
        `stats` summarises the build.
    """
    if mode != "open-only":
        raise ValueError(
            f"foundation seed_bank supports only mode='open-only'; got {mode!r}",
        )

    classifier = FakeCEFRClassifier()
    writer = writer if writer is not None else InMemoryBankWriter()
    checks = phase3_foundation_checks()
    stats = BankStats(mode=mode, seed=seed)
    now = datetime.now(tz=UTC)

    # CE
    for idx, passage in enumerate(_CE_PASSAGES[:target_ce]):
        candidate = synthesize_ce_item(
            CESynthesisInput(
                passage=passage,
                genre=_genre_for_index(idx),
                source="foundation_ce_seed",
                source_id=f"ce-{idx}",
                license="CC-BY-SA-4.0",
                ingested_at=now,
                seed=seed + idx,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(candidate, writer, checks=checks)
        stats.record("CE", outcome.reason)
    stats.per_module.setdefault("CE", ModuleStats()).target = target_ce

    # CO
    for idx, co_seed in enumerate(_CO_SEEDS[:target_co]):
        candidate = synthesize_co_item(
            COSynthesisInput(
                transcript=co_seed.transcript,
                audio_local_path=f"data/cache/audio/{co_seed.source_id}.wav",
                duration_s=co_seed.duration_s,
                accent=co_seed.accent,  # type: ignore[arg-type]
                register=co_seed.register,  # type: ignore[arg-type]
                source=co_seed.source,
                source_id=co_seed.source_id,
                license=co_seed.license,
                ingested_at=now,
                speakers=(Speaker(label="S1", accent=co_seed.accent),),  # type: ignore[arg-type]
                seed=seed + idx,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(candidate, writer, checks=checks)
        stats.record("CO", outcome.reason)
    stats.per_module.setdefault("CO", ModuleStats()).target = target_co

    # EE: round-robin across (task, canadian_context) combinations.
    ee_plan = _plan_ee_targets(target_ee)
    for idx, (task, canadian) in enumerate(ee_plan):
        candidate = synthesize_ee_prompt(
            EESynthesisInput(
                task_number=task,  # type: ignore[arg-type]
                canadian_context=canadian,
                cefr_target="C1",
                seed=seed + idx,
                ingested_at=now,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(candidate, writer, checks=checks)
        stats.record("EE", outcome.reason)
    stats.per_module.setdefault("EE", ModuleStats()).target = target_ee

    # EO: round-robin across task numbers.
    eo_plan = _plan_eo_targets(target_eo)
    for idx, task in enumerate(eo_plan):
        candidate = synthesize_eo_prompt(
            EOSynthesisInput(
                task_number=task,  # type: ignore[arg-type]
                cefr_target="C1",
                seed=seed + idx,
                ingested_at=now,
            ),
            classifier=classifier,
        )
        outcome = load_candidate(candidate, writer, checks=checks)
        stats.record("EO", outcome.reason)
    stats.per_module.setdefault("EO", ModuleStats()).target = target_eo

    # CEFR-level distribution audit across the *currently persisted*
    # bank (not just this run's writes); the operator wants the
    # cumulative shape.
    for item in writer.all_items():
        stats.cefr_levels[item.cefr_level] += 1

    return stats, writer


def _genre_for_index(idx: int) -> str:
    """Distribute CE seeds across the six FEI genres deterministically."""
    return ("news", "narrative", "admin", "letter", "academic", "ad")[idx % 6]


def _plan_ee_targets(target: int) -> list[tuple[int, bool]]:
    """Build a round-robin (task_number, canadian_context) plan.

    Tasks 2 and 3 always require canadian_context=True (ADR-0022).
    Task 1 alternates Canadian/non-Canadian to keep diversity.
    """
    pattern: tuple[tuple[int, bool], ...] = (
        (1, False), (2, True), (3, True), (1, True),
    )
    return [pattern[i % len(pattern)] for i in range(target)]


def _plan_eo_targets(target: int) -> list[int]:
    """Build a round-robin task plan; covers T1/T2/T3 evenly."""
    return [(1 + (i % 3)) for i in range(target)]


# ─── Rendering ────────────────────────────────────────────────


def render(stats: BankStats, writer: InMemoryBankWriter) -> str:
    """Markdown rendering of `stats`; matches the design's BANK_STATS shape."""
    out: list[str] = [
        "# Foundation Bank Build Summary",
        "",
        f"- **Mode**: {stats.mode}",
        f"- **Seed**: {stats.seed}",
        f"- **Total persisted (cumulative)**: {writer.count()}",
        "",
        "## Per-module outcomes",
        "",
        "| Module | Target | Persisted | Already-present | Rejected | Flagged-skipped |",
        "|--------|--------|-----------|------------------|----------|------------------|",
    ]
    for module in ("CO", "CE", "EE", "EO"):
        m = stats.per_module.get(module, ModuleStats())
        out.append(
            f"| {module} | {m.target} | {m.persisted} | "
            f"{m.already_present} | {m.rejected} | {m.flagged_skipped} |",
        )

    out.extend([
        "",
        "## CEFR-level distribution",
        "",
        "| Level | Count | Share |",
        "|-------|-------|-------|",
    ])
    total = max(sum(stats.cefr_levels.values()), 1)
    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        count = stats.cefr_levels.get(level, 0)
        share = count / total
        out.append(f"| {level} | {count} | {share:.1%} |")

    out.extend([
        "",
        "## Per-module sample item ids",
        "",
    ])
    seen: dict[str, list[Item]] = {}
    for item in writer.all_items():
        seen.setdefault(item.module, []).append(item)
    for module in ("CO", "CE", "EE", "EO"):
        sample = seen.get(module, [])[:3]
        if not sample:
            out.append(f"- {module}: (no items)")
            continue
        ids = ", ".join(str(i.id)[:8] for i in sample)
        out.append(f"- {module}: {ids}...")

    out.extend([
        "",
        "*Phase 3 foundation pipeline ran successfully. "
        "Replace `FakeCEFRClassifier` + `InMemoryBankWriter` + the "
        "hardcoded seed pool with the Phase 3 follow-up wiring to "
        "produce a production-grade bank.*",
        "",
    ])
    return "\n".join(out)


# ─── CLI ──────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Build the seed_bank argparse parser."""
    parser = argparse.ArgumentParser(
        prog="seed_bank",
        description=(
            "Phase 3 foundation seed-bank builder. Runs the "
            "deterministic open-only foundation pipeline against "
            "bundled seed data and writes a BankStats summary."
        ),
    )
    parser.add_argument(
        "--mode", default="open-only", choices=["open-only"],
        help="Pipeline mode (only 'open-only' supported in foundation).",
    )
    parser.add_argument("--target-ce", type=int, default=8)
    parser.add_argument("--target-co", type=int, default=4)
    parser.add_argument("--target-ee", type=int, default=4)
    parser.add_argument("--target-eo", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--out", type=str, default="-",
        help="Output path for the BankStats Markdown; '-' (default) means stdout.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
) -> int:
    """CLI entry point.

    Args:
        argv: Argv minus the program name. None ⇒ `sys.argv[1:]`.
        stdout: Where to write the report when ``--out -``. None ⇒
            `sys.stdout`. Tests pass a `StringIO`.

    Returns:
        0 on success; non-zero on failure (e.g., unsupported mode).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    out_stream = stdout if stdout is not None else sys.stdout

    try:
        stats, writer = run_build(
            mode=args.mode,
            target_ce=args.target_ce,
            target_co=args.target_co,
            target_ee=args.target_ee,
            target_eo=args.target_eo,
            seed=args.seed,
        )
    except ValueError as exc:
        print(f"seed_bank: error: {exc}", file=sys.stderr)
        return 2

    report = render(stats, writer)
    if args.out == "-":
        out_stream.write(report)
    else:
        Path(args.out).write_text(report, encoding="utf-8")
    return 0


# Convenience for tests that want to capture the rendered output
# without touching real stdout.
def main_capture(argv: Sequence[str] | None = None) -> tuple[int, str]:
    """Run `main` capturing the stdout report; returns ``(exit_code, text)``."""
    buf = StringIO()
    code = main(argv, stdout=buf)
    return code, buf.getvalue()


__all__ = [
    "BankStats",
    "ModuleStats",
    "main",
    "main_capture",
    "render",
    "run_build",
]
