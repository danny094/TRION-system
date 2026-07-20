"""
Cron Server — MCP Entry Point

Verwaltet autonome Cron-Jobs die TRION-Objectives zeitgesteuert ausführen.
Läuft als eigenständiger Service — kein direkter Import von außen.

Start: python server.py
"""

from fastmcp import FastMCP

mcp = FastMCP("cron-server")


# ── Job Management ────────────────────────────────────────

@mcp.tool
def cron_list() -> dict:
    """Listet alle konfigurierten Cron-Jobs."""
    from scheduler import get_scheduler
    return get_scheduler().list_jobs()


@mcp.tool
def cron_get(job_id: str) -> dict:
    """Details zu einem Cron-Job."""
    from scheduler import get_scheduler
    return get_scheduler().get_job(job_id)


@mcp.tool
def cron_create(objective: str, schedule: str, label: str = "") -> dict:
    """Erstellt einen neuen Cron-Job.

    Args:
        objective: Was TRION tun soll (z.B. 'Erstelle täglich einen Status-Report')
        schedule:  Cron-Ausdruck (z.B. '0 8 * * *') oder Kurzform ('daily', 'hourly')
        label:     Optionaler Anzeigename
    """
    from scheduler import get_scheduler
    return get_scheduler().create_job(objective=objective, schedule=schedule, label=label)


@mcp.tool
def cron_update(job_id: str, updates: dict) -> dict:
    """Aktualisiert einen Cron-Job (schedule, objective, label)."""
    from scheduler import get_scheduler
    return get_scheduler().update_job(job_id, updates)


@mcp.tool
def cron_delete(job_id: str) -> dict:
    """Löscht einen Cron-Job."""
    from scheduler import get_scheduler
    return get_scheduler().delete_job(job_id)


@mcp.tool
def cron_pause(job_id: str) -> dict:
    """Pausiert einen Cron-Job."""
    from scheduler import get_scheduler
    return get_scheduler().pause_job(job_id)


@mcp.tool
def cron_resume(job_id: str) -> dict:
    """Setzt einen pausierten Cron-Job fort."""
    from scheduler import get_scheduler
    return get_scheduler().resume_job(job_id)


@mcp.tool
def cron_run_now(job_id: str) -> dict:
    """Führt einen Cron-Job sofort aus (unabhängig vom Schedule)."""
    from scheduler import get_scheduler
    return get_scheduler().run_now(job_id)


# ── Validation ────────────────────────────────────────────

@mcp.tool
def cron_validate(objective: str, schedule: str) -> dict:
    """Validiert einen Cron-Ausdruck und prüft ob das Objective erlaubt ist."""
    from scheduler import validate_cron
    return validate_cron(objective=objective, schedule=schedule)


@mcp.tool
def cron_status() -> dict:
    """Status des Cron-Schedulers (laufend, Anzahl Jobs, nächste Ausführungen)."""
    from scheduler import get_scheduler
    return get_scheduler().status()


@mcp.tool
def cron_queue() -> dict:
    """Zeigt die nächsten geplanten Ausführungen."""
    from scheduler import get_scheduler
    return get_scheduler().get_queue()


# ── Server Start ───────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
