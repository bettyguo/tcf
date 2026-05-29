"""Tests for the CEFR classifier implementations."""

from __future__ import annotations

from pathlib import Path

import pytest
from tcf_accel.errors import CEFRClassifierUnavailableError
from tcf_accel_content.cefr import CEFR_LEVELS, CEFRClassifier
from tcf_accel_content.cefr.classify import (
    CamembertCEFRClassifier,
    FakeCEFRClassifier,
    load_classifier,
)


def test_fake_is_protocol_conformant() -> None:
    clf = FakeCEFRClassifier()
    assert isinstance(clf, CEFRClassifier)


def test_fake_is_deterministic() -> None:
    clf = FakeCEFRClassifier()
    a = clf.classify("Bonjour, je m'appelle Marie.")
    b = clf.classify("Bonjour, je m'appelle Marie.")
    assert a == b


def test_fake_returns_valid_prediction_shape() -> None:
    clf = FakeCEFRClassifier()
    pred = clf.classify("Texte de test.")
    assert pred.level in CEFR_LEVELS
    assert pred.classifier_version == "fake-v0"
    assert len(pred.text_sha256) == 64  # hex sha256
    # Distribution covers all six levels and sums to ~1.
    assert set(pred.distribution.keys()) == set(CEFR_LEVELS)
    assert abs(sum(pred.distribution.values()) - 1.0) < 1e-9
    # Argmax matches reported level + confidence.
    argmax_level = max(pred.distribution, key=lambda k: pred.distribution[k])
    assert argmax_level == pred.level
    assert pred.confidence == pytest.approx(pred.distribution[pred.level])


def test_fake_batch_matches_single() -> None:
    clf = FakeCEFRClassifier()
    texts = ["a", "bb", "ccc"]
    batch = clf.classify_batch(texts)
    single = [clf.classify(t) for t in texts]
    assert batch == single


def test_fake_differs_on_different_text() -> None:
    clf = FakeCEFRClassifier()
    samples = {clf.classify(c * 32).text_sha256 for c in "abcdef"}
    # All six hashes are distinct (collision-free with overwhelming prob.).
    assert len(samples) == 6


def test_camembert_constructor_refuses_without_artifact() -> None:
    with pytest.raises(CEFRClassifierUnavailableError):
        CamembertCEFRClassifier(artifact_dir=Path("/does/not/exist"))


def test_camembert_constructor_refuses_when_artifact_present_but_unwired(
    tmp_path: Path,
) -> None:
    # The directory exists but the real impl is not wired yet; the
    # constructor still raises with a clear message.
    artifact = tmp_path / "cefr-v0.3.1"
    artifact.mkdir()
    with pytest.raises(CEFRClassifierUnavailableError) as exc_info:
        CamembertCEFRClassifier(artifact_dir=artifact)
    assert "not yet implemented" in str(exc_info.value)


def test_load_classifier_falls_back_to_fake_when_artifact_missing() -> None:
    clf = load_classifier(Path("/does/not/exist"))
    assert isinstance(clf, FakeCEFRClassifier)


def test_load_classifier_falls_back_to_fake_when_no_artifact_given() -> None:
    clf = load_classifier()
    assert isinstance(clf, FakeCEFRClassifier)


def test_load_classifier_refuses_when_allow_fake_false() -> None:
    with pytest.raises(CEFRClassifierUnavailableError):
        load_classifier(Path("/does/not/exist"), allow_fake=False)
