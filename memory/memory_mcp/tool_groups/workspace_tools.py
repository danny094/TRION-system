from typing import Dict, Optional

from ..db.workspace import (
    save_workspace_entry, list_workspace_entries,
    get_workspace_entry, update_workspace_entry, delete_workspace_entry,
)


def register_workspace_tools(mcp) -> None:

    @mcp.tool
    def workspace_save(
        conversation_id: str,
        content: str,
        entry_type: str = "observation",
        source_layer: str = "thinking",
    ) -> Dict:
        """Speichert einen Workspace-Eintrag."""
        entry_id = save_workspace_entry(conversation_id, content, entry_type, source_layer)
        return {"structuredContent": {"id": entry_id, "conversation_id": conversation_id, "entry_type": entry_type, "source_layer": source_layer}}

    @mcp.tool
    def workspace_list(
        conversation_id: Optional[str] = None,
        limit: int = 50,
        entry_type: Optional[str] = None,
    ) -> Dict:
        """Listet Workspace-Einträge, optional gefiltert."""
        entries = list_workspace_entries(conversation_id, limit, entry_type)
        return {"structuredContent": {"entries": entries, "count": len(entries)}}

    @mcp.tool
    def workspace_get(entry_id: int) -> Dict:
        """Gibt einen einzelnen Workspace-Eintrag zurück."""
        entry = get_workspace_entry(entry_id)
        return {"structuredContent": entry} if entry else {"structuredContent": {"error": f"Entry {entry_id} not found"}}

    @mcp.tool
    def workspace_update(entry_id: int, content: str) -> Dict:
        """Aktualisiert den Inhalt eines Workspace-Eintrags."""
        updated = update_workspace_entry(entry_id, content)
        return {"structuredContent": {"updated": updated, "entry_id": entry_id}}

    @mcp.tool
    def workspace_delete(entry_id: int) -> Dict:
        """Löscht einen Workspace-Eintrag."""
        deleted = delete_workspace_entry(entry_id)
        return {"structuredContent": {"deleted": deleted, "entry_id": entry_id}}
