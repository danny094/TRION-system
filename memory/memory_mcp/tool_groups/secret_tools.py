from ..db.secrets import save_secret, get_secret_value, list_secrets, delete_secret


def register_secret_tools(mcp) -> None:

    @mcp.tool
    def secret_save(name: str, value: str) -> dict:
        """Speichert oder aktualisiert ein verschlüsseltes API-Secret."""
        try:
            save_secret(name, value)
            return {"success": True, "name": name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def secret_get(name: str) -> dict:
        """Gibt den entschlüsselten Wert eines Secrets zurück. Nur intern."""
        val = get_secret_value(name)
        if val is None:
            return {"value": None, "error": f"Secret '{name}' not found"}
        return {"value": val}

    @mcp.tool
    def secret_list() -> dict:
        """Listet alle Secret-Namen (Werte werden nie zurückgegeben)."""
        return {"secrets": list_secrets()}

    @mcp.tool
    def secret_delete(name: str) -> dict:
        """Löscht ein Secret per Name."""
        return {"success": delete_secret(name), "name": name}
