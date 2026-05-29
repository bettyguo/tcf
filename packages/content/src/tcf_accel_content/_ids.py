"""Deterministic item-id derivation.

Per `phase3_design.md §1.2`, `Item.id` is a UUIDv5 over
`(source, source_id, synthesizer_version, prompt_hash, seed)`. Two
consequences:

- Re-running synthesis with identical inputs yields the same id;
  `INSERT … ON CONFLICT (id) DO NOTHING` makes the loader idempotent.
- A prompt or model change produces a *new* id; the old item is
  preserved for reproducibility (and may be retired separately).

The namespace is fixed at module load. Changing it would re-key the
entire bank and is therefore forbidden without an ADR.
"""

from __future__ import annotations

from uuid import UUID, uuid5

from tcf_accel.ids import ItemId

# UUIDv4 generated once for this project. Treat as a frozen constant;
# changing it would invalidate every derived item id in the bank.
_NAMESPACE: UUID = UUID("9c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f")


def derive_item_id(
    *,
    source: str,
    source_id: str,
    synthesizer_version: str,
    prompt_hash: str,
    seed: int,
) -> ItemId:
    """Derive a stable `ItemId` from the synthesis inputs.

    The components are joined by ``|`` (a character not used inside any
    of the inputs by construction; source/source-id are
    SPDX-like / dataset-native identifiers and prompt_hash is hex).

    Args:
        source: Logical source identifier (e.g. ``"common_voice_fr_v17"``).
        source_id: Stable id within the source.
        synthesizer_version: The synthesizer artifact version
            (e.g. ``"ce-v0.3.1"``); a bump produces a new id even for
            the same passage.
        prompt_hash: SHA-256 of the rendered LLM prompt.
        seed: Synthesis seed (any non-negative integer).

    Returns:
        A UUIDv5 wrapped as `ItemId`.

    Example:
        >>> a = derive_item_id(
        ...     source="common_voice_fr_v17", source_id="42",
        ...     synthesizer_version="ce-v0.3.1",
        ...     prompt_hash="0" * 64, seed=7,
        ... )
        >>> b = derive_item_id(
        ...     source="common_voice_fr_v17", source_id="42",
        ...     synthesizer_version="ce-v0.3.1",
        ...     prompt_hash="0" * 64, seed=7,
        ... )
        >>> a == b
        True

    Complexity: O(len(joined)) for SHA-1 under the hood of UUIDv5.
    """
    payload = "|".join(
        (source, source_id, synthesizer_version, prompt_hash, str(seed)),
    )
    return ItemId(uuid5(_NAMESPACE, payload))


__all__ = ["derive_item_id"]
