"""Tests for `tcf_accel_content._ids.derive_item_id`."""

from __future__ import annotations

from uuid import UUID

from tcf_accel_content._ids import derive_item_id


def _kwargs():
    return {
        "source": "common_voice_fr_v17",
        "source_id": "42",
        "synthesizer_version": "ce-v0.3.1",
        "prompt_hash": "0" * 64,
        "seed": 7,
    }


def test_derive_is_deterministic() -> None:
    a = derive_item_id(**_kwargs())
    b = derive_item_id(**_kwargs())
    assert a == b


def test_derive_returns_uuid_v5() -> None:
    a = derive_item_id(**_kwargs())
    # UUIDv5 encodes its version into byte 6's high nibble.
    assert isinstance(a, UUID)
    assert a.version == 5


def test_derive_changes_on_source_id() -> None:
    a = derive_item_id(**_kwargs())
    b = derive_item_id(**{**_kwargs(), "source_id": "43"})
    assert a != b


def test_derive_changes_on_synthesizer_version() -> None:
    # phase3_design.md §1.2: bumping the synthesizer version yields a
    # new item id rather than mutating the old one.
    a = derive_item_id(**_kwargs())
    b = derive_item_id(**{**_kwargs(), "synthesizer_version": "ce-v0.3.2"})
    assert a != b


def test_derive_changes_on_seed() -> None:
    a = derive_item_id(**_kwargs())
    b = derive_item_id(**{**_kwargs(), "seed": 8})
    assert a != b


def test_derive_changes_on_prompt_hash() -> None:
    a = derive_item_id(**_kwargs())
    b = derive_item_id(**{**_kwargs(), "prompt_hash": "f" * 64})
    assert a != b
