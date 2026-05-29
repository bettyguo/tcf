"""Item synthesizers (one module per TCF module: co, ce, ee, eo).

Each per-module file (Phase 3) exposes a `synthesize_<module>_item` /
`synthesize_<module>_prompt` entry point taking a typed dataclass input
and returning a `CandidateItem` (see `tcf_accel_content.types`). All
four entry points share `_llm.py` for the LLM call wrapper with VCR-
cassette test mode.

ADR-0018 governs the authoring shape; ADR-0021 the synthetic cap.
"""

from __future__ import annotations

# Phase 3 implementation will populate these aliases:
# from tcf_accel_content.synthesize.ce import synthesize_ce_item
# from tcf_accel_content.synthesize.co import synthesize_co_item
# from tcf_accel_content.synthesize.ee import synthesize_ee_prompt
# from tcf_accel_content.synthesize.eo import synthesize_eo_prompt

__all__: list[str] = []
