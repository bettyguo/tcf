"""Tests for `FixtureSource` and the source allowlist."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tcf_accel_content.sources import (
    REDISTRIBUTABLE_LICENSE_ALLOWLIST,
    Source,
    license_compatible,
)
from tcf_accel_content.sources.fixture import FixtureSource


def test_allowlist_contains_expected_spdx_ids() -> None:
    assert {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "PublicDomain"} <= (
        REDISTRIBUTABLE_LICENSE_ALLOWLIST
    )


def test_license_compatible_accepts_allowlisted() -> None:
    assert license_compatible("CC0-1.0")
    assert license_compatible("CC-BY-SA-4.0")


def test_license_compatible_rejects_non_allowlisted() -> None:
    assert not license_compatible("proprietary")
    assert not license_compatible("CC-BY-NC-ND-4.0")  # TEDx; phase3_design.md §2.1
    assert not license_compatible("RFI-TOS-personal-study")


def _write_manifest(p: Path, records: list[dict]) -> None:
    lines = "\n".join(json.dumps(r) for r in records)
    p.write_text(lines + "\n", encoding="utf-8")


def test_fixture_source_conforms_to_protocol(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    _write_manifest(manifest, [
        {"kind": "text", "source": "wikisource_fr", "source_id": "1",
         "license": "CC-BY-SA-4.0", "text": "Bonjour."},
    ])
    s = FixtureSource(
        name="wikisource_fr", license="CC-BY-SA-4.0",
        redistributable=True, manifest_path=manifest,
    )
    assert isinstance(s, Source)


def test_fixture_source_yields_records(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    _write_manifest(manifest, [
        {"kind": "text", "source": "wikisource_fr", "source_id": "1",
         "license": "CC-BY-SA-4.0",
         "fetched_at": "2026-05-27T00:00:00+00:00",
         "text": "Bonjour le monde."},
        {"kind": "text", "source": "wikisource_fr", "source_id": "2",
         "license": "CC-BY-SA-4.0",
         "fetched_at": "2026-05-28T00:00:00+00:00",
         "text": "Au revoir."},
    ])
    s = FixtureSource(
        name="wikisource_fr", license="CC-BY-SA-4.0",
        redistributable=True, manifest_path=manifest,
    )
    assets = list(s.iter_assets())
    assert [a.source_id for a in assets] == ["1", "2"]
    assert assets[0].text == "Bonjour le monde."


def test_fixture_source_honours_limit(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    _write_manifest(manifest, [
        {"kind": "text", "source": "s", "source_id": str(i),
         "license": "CC0-1.0", "text": f"item {i}"}
        for i in range(5)
    ])
    s = FixtureSource(
        name="s", license="CC0-1.0", redistributable=True, manifest_path=manifest,
    )
    assets = list(s.iter_assets(limit=2))
    assert len(assets) == 2


def test_fixture_source_honours_since(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    _write_manifest(manifest, [
        {"kind": "text", "source": "s", "source_id": "old",
         "license": "CC0-1.0",
         "fetched_at": "2025-01-01T00:00:00+00:00",
         "text": "old"},
        {"kind": "text", "source": "s", "source_id": "new",
         "license": "CC0-1.0",
         "fetched_at": "2026-06-01T00:00:00+00:00",
         "text": "new"},
    ])
    s = FixtureSource(
        name="s", license="CC0-1.0", redistributable=True, manifest_path=manifest,
    )
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    assets = list(s.iter_assets(since=cutoff))
    assert [a.source_id for a in assets] == ["new"]


def test_fixture_source_resolves_bytes_path(tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF....fakewav")
    manifest = tmp_path / "m.jsonl"
    _write_manifest(manifest, [
        {"kind": "audio", "source": "cv", "source_id": "1",
         "license": "CC0-1.0", "bytes_path": "clip.wav"},
    ])
    s = FixtureSource(
        name="cv", license="CC0-1.0", redistributable=True, manifest_path=manifest,
    )
    asset = next(s.iter_assets())
    assert asset.kind == "audio"
    assert asset.bytes_path is not None
    assert asset.bytes_path.resolve() == audio.resolve()


def test_fixture_source_ignores_blank_and_comment_lines(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    manifest.write_text(
        "\n"
        "# a comment\n"
        + json.dumps({"kind": "text", "source": "s", "source_id": "1",
                      "license": "CC0-1.0", "text": "hi"}) + "\n",
        encoding="utf-8",
    )
    s = FixtureSource(
        name="s", license="CC0-1.0", redistributable=True, manifest_path=manifest,
    )
    assets = list(s.iter_assets())
    assert len(assets) == 1


def test_fixture_source_rejects_malformed_json(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    manifest.write_text("{not json\n", encoding="utf-8")
    s = FixtureSource(
        name="s", license="CC0-1.0", redistributable=True, manifest_path=manifest,
    )
    with pytest.raises(ValueError, match="invalid JSON"):
        list(s.iter_assets())


def test_fixture_source_rejects_missing_required_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "m.jsonl"
    _write_manifest(manifest, [{"kind": "text", "source": "s"}])  # missing source_id, license
    s = FixtureSource(
        name="s", license="CC0-1.0", redistributable=True, manifest_path=manifest,
    )
    with pytest.raises(ValueError, match="missing required field"):
        list(s.iter_assets())
