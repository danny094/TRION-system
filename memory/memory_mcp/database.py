"""
database — thin re-exporter for backwards compatibility.

All logic lives in db/ subpackage. Import directly from there for new code:
  from memory_mcp.db.memory import insert_row
  from memory_mcp.db.facts import load_fact
"""
from .db import (  # noqa: F401
    init_db, migrate_db,
    insert_row, row_to_memory_dict,
    insert_fact, load_fact, row_to_fact_dict,
    upsert_skill_metric, get_skill_metric, list_skill_metrics, update_skill_status,
    save_workspace_entry, list_workspace_entries, get_workspace_entry,
    update_workspace_entry, delete_workspace_entry,
    get_unpromoted_entries, mark_promoted,
    get_conversation_meta, upsert_conversation_meta,
    get_conversation_write_policy, evaluate_long_term_write,
    save_secret, get_secret_value, list_secrets, delete_secret,
    artifact_save, artifact_get, artifact_list, artifact_update,
)
