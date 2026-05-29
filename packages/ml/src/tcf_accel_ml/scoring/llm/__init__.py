"""LLM critic: protocol + stub + cloud adapter."""

from __future__ import annotations

from tcf_accel_ml.scoring.llm.critic import LLMCritic, LLMCritique, SuggestedRewrite
from tcf_accel_ml.scoring.llm.prompts import build_ee_prompt, build_eo_prompt
from tcf_accel_ml.scoring.llm.stub import LLMCriticStub

__all__ = [
    "LLMCritic",
    "LLMCriticStub",
    "LLMCritique",
    "SuggestedRewrite",
    "build_ee_prompt",
    "build_eo_prompt",
]
