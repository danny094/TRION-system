"""
config.output
=============
Ausgabe-Verhalten — Längen, Timeouts, Stream & Job-Kapazitäten.

Module:
  char_limits → Hard-Caps & Soft-Targets für interactive/analytical/deep
  streaming   → Output-Timeouts & Stream-Postcheck-Mode
  jobs        → Deep-Job & Autonomy-Job Kapazitäten auf API-Ebene

Re-Exports für bequemen Zugriff via `from config.output import ...`:
"""
from config.output.char_limits import (
    get_output_char_cap_interactive,
    get_output_char_cap_interactive_long,
    get_output_char_cap_interactive_analytical,
    get_output_char_cap_deep,
    get_output_char_target_interactive,
    get_output_char_target_interactive_analytical,
    get_output_char_target_deep,
)

from config.output.streaming import (
    get_output_timeout_interactive_s,
    get_output_timeout_deep_s,
    get_output_stream_postcheck_mode,
)

from config.output.jobs import (
    get_deep_job_timeout_s,
    get_deep_job_max_concurrency,
    get_autonomy_job_timeout_s,
    get_autonomy_job_max_concurrency,
)
from config.output.evidence import (
    get_output_multi_tool_synthesis_enable,
    get_output_renderable_evidence_max_items,
    get_output_renderable_evidence_max_bullets_per_item,
)

__all__ = [
    # char_limits
    "get_output_char_cap_interactive", "get_output_char_cap_interactive_long",
    "get_output_char_cap_interactive_analytical", "get_output_char_cap_deep",
    "get_output_char_target_interactive", "get_output_char_target_interactive_analytical",
    "get_output_char_target_deep",
    # streaming
    "get_output_timeout_interactive_s", "get_output_timeout_deep_s",
    "get_output_stream_postcheck_mode",
    # jobs
    "get_deep_job_timeout_s", "get_deep_job_max_concurrency",
    "get_autonomy_job_timeout_s", "get_autonomy_job_max_concurrency",
    # evidence
    "get_output_multi_tool_synthesis_enable",
    "get_output_renderable_evidence_max_items",
    "get_output_renderable_evidence_max_bullets_per_item",
]
