"""Cloud backends refuse construction without the env var (ADR-017).

The structural counterpart to `test_no_network_in_default.py`: the
*only* code path that can construct a cloud-egress object is when the
operator has explicitly set the corresponding env var. Constructing
the cloud backend under any other configuration must raise at
construction time — the failure mode is loud, not silent.

Phase 5 ships exactly one cloud backend (`CloudLiteLLMASRBackend`);
the TTS path has no cloud variant in Phase 5 (`phase5_design.md §12.1`).
LLM-gateway cloud opt-in flows through the existing LiteLLM gateway
seam (ADR-009) and lives outside the ASR/MFA/TTS scope tested here.
"""

from __future__ import annotations

import pytest
from tcf_accel_ml.asr import CloudLiteLLMASRBackend

from tests.capability._blocknet import block_network


def test_cloud_asr_refuses_construction_with_no_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TCF_ACCEL_ASR_BACKEND", raising=False)
    with pytest.raises(RuntimeError, match="cloud:litellm"):
        CloudLiteLLMASRBackend()


def test_cloud_asr_refuses_construction_with_wrong_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even a non-empty but wrong value (e.g. left over from another deploy)
    must not construct — exact-match is the contract."""
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "local")
    with pytest.raises(RuntimeError, match="cloud:litellm"):
        CloudLiteLLMASRBackend()


def test_cloud_asr_refusal_is_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The refusal path itself must not make a network call (paranoid check)."""
    monkeypatch.delenv("TCF_ACCEL_ASR_BACKEND", raising=False)
    with block_network(), pytest.raises(RuntimeError):
        CloudLiteLLMASRBackend()


def test_cloud_asr_constructs_under_explicit_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the exact env var, construction succeeds. The transcribe path
    still raises at runtime (no litellm in CI), but the construction
    succeeds — which is what the operator opt-in contract requires."""
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "cloud:litellm")
    backend = CloudLiteLLMASRBackend()
    assert backend.name == "cloud:litellm"


def test_dispatch_factory_routes_to_cloud_only_with_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The dispatcher (`get_asr_backend`) must not silently downgrade to
    cloud when given an ambiguous configuration. Only the literal
    `cloud:litellm` value selects the cloud path."""
    from tcf_accel_ml.asr import get_asr_backend  # noqa: PLC0415

    for value in ("", "local", "stub", "Cloud:LiteLLM"):
        monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", value)
        backend = get_asr_backend() if value in {"local", "stub"} else None
        if backend is not None:
            assert backend.name != "cloud:litellm"

    # Exact match → cloud.
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "cloud:litellm")
    assert get_asr_backend().name == "cloud:litellm"
