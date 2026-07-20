"""
Skill Server — MCP Entry Point

Installiert, verwaltet und führt Skills aus.
Skills sind isolierte, sandboxed Python-Funktionen die TRION erweitern.

Start: python server.py
"""

from fastmcp import FastMCP

mcp = FastMCP("skill-server")


# ── Skill Management ───────────────────────────────────────

@mcp.tool
def list_skills(category: str = None) -> dict:
    """Listet alle installierten Skills."""
    from skill_manager import SkillManager
    return SkillManager().list_skills(category=category)


@mcp.tool
def get_skill_info(name: str) -> dict:
    """Details zu einem Skill."""
    from skill_manager import SkillManager
    return SkillManager().get_skill(name)


@mcp.tool
def install_skill(name: str, code: str, description: str = "", triggers: list = None) -> dict:
    """Installiert einen neuen Skill."""
    from skill_manager import SkillManager
    return SkillManager().install(name, code, description=description, triggers=triggers or [])


@mcp.tool
def uninstall_skill(name: str) -> dict:
    """Deinstalliert einen Skill."""
    from skill_manager import SkillManager
    return SkillManager().uninstall(name)


@mcp.tool
def run_skill(name: str, args: dict = None) -> dict:
    """Führt einen installierten Skill aus."""
    from skill_manager import SkillManager
    return SkillManager().run(name, args or {})


# ── Knowledge ─────────────────────────────────────────────

@mcp.tool
def search_skill_knowledge(query: str, limit: int = 5) -> dict:
    """Semantische Suche in der Skill-Wissensbasis."""
    from skill_knowledge import search
    return {"results": search(query, limit=limit)}


@mcp.tool
def get_skill_categories() -> dict:
    """Alle verfügbaren Skill-Kategorien."""
    from skill_knowledge import get_categories
    return {"categories": get_categories()}


# ── Validation ────────────────────────────────────────────

@mcp.tool
def validate_skill_code(code: str) -> dict:
    """Prüft Skill-Code auf Sicherheit und Qualität vor der Installation."""
    from skill_cim_light import validate_code
    return validate_code(code)


# ── Server Start ───────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
