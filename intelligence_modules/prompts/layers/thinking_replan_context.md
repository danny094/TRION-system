---
scope: layer_prompt
target: thinking_replan_context
variables: ["failed_step_id", "failure_status", "failure_error", "replan_count", "artifacts_json"]
status: active
---

REPLAN-KONTEXT:
- Fehlgeschlagener Schritt: {failed_step_id}
- Status: {failure_status}
- Fehler: {failure_error}
- Bisherige Replans: {replan_count}

ARTEFAKTE BISHER:
{artifacts_json}
