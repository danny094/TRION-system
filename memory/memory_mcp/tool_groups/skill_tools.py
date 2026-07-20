from typing import Dict, Optional

from ..db.skill_metrics import (
    upsert_skill_metric, get_skill_metric,
    list_skill_metrics, update_skill_status,
)


def register_skill_tools(mcp) -> None:

    @mcp.tool
    def skill_metric_record(
        skill_id: str,
        success: bool,
        exec_time_ms: float,
        error: Optional[str] = None,
        version: str = "1.0",
    ) -> Dict:
        """Zeichnet ein Skill-Ausführungsergebnis auf."""
        row_id = upsert_skill_metric(skill_id, success, exec_time_ms, error, version)
        return {"structuredContent": {"recorded": True, "skill_id": skill_id, "row_id": row_id}}

    @mcp.tool
    def skill_metric_get(skill_id: str) -> Dict:
        """Gibt Metriken für einen einzelnen Skill zurück."""
        metric = get_skill_metric(skill_id)
        return {"structuredContent": metric} if metric else {"structuredContent": {"error": f"No metrics for {skill_id}"}}

    @mcp.tool
    def skill_metrics_list(status: Optional[str] = None, limit: int = 50) -> Dict:
        """Listet alle Skill-Metriken, optional nach Status gefiltert."""
        metrics = list_skill_metrics(status, limit)
        return {"structuredContent": {"metrics": metrics, "count": len(metrics)}}

    @mcp.tool
    def skill_metric_set_status(skill_id: str, status: str) -> Dict:
        """Setzt den Status eines Skills (active/deprecated/beta)."""
        updated = update_skill_status(skill_id, status)
        return {"structuredContent": {"updated": updated, "skill_id": skill_id, "status": status}}
