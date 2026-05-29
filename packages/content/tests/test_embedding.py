"""Tests for the embedder implementations."""

from __future__ import annotations

import pytest
from tcf_accel_content.embedding import EMBEDDER_DIM, Embedder
from tcf_accel_content.embedding.embed import (
    FakeEmbedder,
    MPNetEmbedder,
    load_embedder,
)


def test_fake_is_protocol_conformant() -> None:
    e = FakeEmbedder()
    assert isinstance(e, Embedder)


def test_fake_is_deterministic() -> None:
    e = FakeEmbedder()
    a = e.embed("le chat dort")
    b = e.embed("le chat dort")
    assert a == b


def test_fake_returns_correct_dim() -> None:
    v = FakeEmbedder().embed("salut")
    assert len(v) == EMBEDDER_DIM == 768


def test_fake_is_l2_normalised() -> None:
    v = FakeEmbedder().embed("salut")
    norm_sq = sum(x * x for x in v)
    assert norm_sq == pytest.approx(1.0, abs=1e-9)


def test_fake_differs_on_different_text() -> None:
    e = FakeEmbedder()
    a = e.embed("aaa")
    b = e.embed("bbb")
    # Different inputs → different vectors; not byte-equal.
    assert a != b
    # And the dot product is far from 1 (i.e., not the same direction).
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    assert dot < 0.5


def test_fake_batch_matches_single() -> None:
    e = FakeEmbedder()
    batch = e.embed_batch(["a", "b", "c"])
    single = [e.embed(t) for t in ["a", "b", "c"]]
    assert batch == single


def test_mpnet_constructor_refuses_until_wired() -> None:
    with pytest.raises(NotImplementedError):
        MPNetEmbedder()


def test_load_embedder_falls_back_to_fake() -> None:
    e = load_embedder()
    assert isinstance(e, FakeEmbedder)


def test_load_embedder_refuses_when_allow_fake_false() -> None:
    with pytest.raises(NotImplementedError):
        load_embedder(allow_fake=False)
