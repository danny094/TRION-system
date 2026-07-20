import os

from config.infra.adapter import settings


def get_output_multi_tool_synthesis_enable() -> bool:
    return str(
        settings.get(
            "OUTPUT_MULTI_TOOL_SYNTHESIS_ENABLE",
            os.getenv("OUTPUT_MULTI_TOOL_SYNTHESIS_ENABLE", "true"),
        )
    ).strip().lower() == "true"


def get_output_renderable_evidence_max_items() -> int:
    try:
        val = int(
            settings.get(
                "OUTPUT_RENDERABLE_EVIDENCE_MAX_ITEMS",
                os.getenv("OUTPUT_RENDERABLE_EVIDENCE_MAX_ITEMS", "4"),
            )
        )
    except Exception:
        val = 4
    return max(1, min(12, val))


def get_output_renderable_evidence_max_bullets_per_item() -> int:
    try:
        val = int(
            settings.get(
                "OUTPUT_RENDERABLE_EVIDENCE_MAX_BULLETS_PER_ITEM",
                os.getenv("OUTPUT_RENDERABLE_EVIDENCE_MAX_BULLETS_PER_ITEM", "4"),
            )
        )
    except Exception:
        val = 4
    return max(0, min(12, val))
