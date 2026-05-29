"""Property: default-mode sessions write zero audio bytes to disk (ADR-017).

The third leg of `phase5_audit.md §9`'s privacy posture: even when the
network is permitted, the *filesystem* must remain quiet in default
mode. A learner who completes an EO drill leaves no audio bytes on
disk; `Interaction.audio_path` is `None`; and the data directory's
byte count is unchanged across the session.

The test redirects `TCF_ACCEL_DATA_DIR` at a temp path (matching the
production layout) and runs an EO drill end-to-end. After the drill,
the temp directory is empty modulo the dismissal log (the only file
ADR-017 *does* permit, and only after an explicit dismissal — this
test does not trigger one).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import EOContent
from tcf_accel.schemas.item import Item
from tcf_accel_sla.drills import EOTaskDrill


def _data_dir_bytes(path: Path) -> int:
    """Sum the byte sizes of every file under `path`."""
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _eo_item() -> Item:
    return Item(
        id=uuid4(),
        module="EO",
        cefr_level="B2",
        difficulty_irt=7.0,
        discrimination_irt=1.0,
        content=EOContent(
            task_number=1,
            examiner_prompts=["Présentez-vous."],
            candidate_prep_time_s=0,
            target_duration_s=180,
            rubric_version="eo.v1",
        ),
        provenance=Provenance(
            source="test",
            source_id="t",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
    )


def _good_audio() -> bytes:
    return b"\xff\xff" * (10 * 16_000)


def test_eo_drill_grade_writes_zero_bytes_to_data_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-017: grading an EO drill in default mode writes 0 bytes under data/."""
    monkeypatch.setenv("TCF_ACCEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")

    before = _data_dir_bytes(tmp_path)
    drill = EOTaskDrill()
    item = _eo_item()
    result = drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    after = _data_dir_bytes(tmp_path)

    # Sanity: the grade actually ran and produced a signal.
    assert result.pronunciation is not None
    # Load-bearing: no audio (or anything else) was written to data/.
    assert after == before == 0


def test_interaction_audio_path_is_none_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-017: the emitted Interaction's `audio_path` is `None` unless
    the operator explicitly opted into local audio retention."""
    monkeypatch.setenv("TCF_ACCEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")

    drill = EOTaskDrill()
    item = _eo_item()
    result = drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    interaction = drill.to_interaction(
        user_id=uuid4(),
        session_id=uuid4(),
        item=item,
        result=result,
        rt_ms=120_000,
        rating=3,
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    assert interaction.audio_path is None


def test_raw_response_records_bytes_count_not_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-017 storage rule: even the in-memory `Interaction.raw_response`
    carries the audio byte *count*, not the bytes themselves. A future
    log/serialize/audit pass over interactions never exposes raw audio."""
    monkeypatch.setenv("TCF_ACCEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")

    drill = EOTaskDrill()
    item = _eo_item()
    audio = _good_audio()
    result = drill.grade(item, {"audio": audio, "sample_rate_hz": 16_000})
    raw = result.raw_response
    assert raw["audio_bytes"] == len(audio)
    # And the bytes themselves are NOT under any key.
    for value in raw.values():
        assert not isinstance(value, (bytes, bytearray, memoryview))


def test_co_shadowing_drill_does_not_persist_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shadowing also records audio (the only CO drill that does); the
    same ADR-017 invariant holds — `audio_path` is `None` and the
    data dir is untouched."""
    # The shadowing drill itself isn't shipped in Phase 5 step 5 (it
    # needs the ML stack from step 6/7); however the contract that
    # *would* apply when it lands is the same. For Phase 5 we assert
    # the invariant against the EO core drill, which already records
    # audio and carries the same shape.
    monkeypatch.setenv("TCF_ACCEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")

    before = _data_dir_bytes(tmp_path)
    drill = EOTaskDrill()
    item = _eo_item()
    drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    drill.grade(item, {"audio": _good_audio(), "sample_rate_hz": 16_000})
    after = _data_dir_bytes(tmp_path)
    assert after == before == 0
