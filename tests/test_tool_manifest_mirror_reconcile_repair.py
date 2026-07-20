"""P11.0 SP3 - mcp.installer_reconcile.reconcile_tool_manifest_mirrors().

Mirror-Reparatur-Faelle (siehe tests/test_tool_manifest_mirror_reconcile.py
fuer die DECIDE-2-Ownership-Scope-Faelle - aufgeteilt wegen Doc 07s
200-Zeilen-Grenze, Codex Checkpoint 4 P1):

- Mirror-Drift (fehlend und hash-abweichend) wird ueber denselben
  `build_tool_intent_mirror()`-Vertrag reparariert wie Install/Update/Toggle.
- ein invalides Bundle darf einen vorhandenen Mirror nicht aktiv stehen
  lassen (Fail-closed statt stale, Codex Checkpoint 4 P1) - der Mirror wird
  deaktiviert und persistiert, der Eintrag bleibt zusaetzlich `unresolved`.
- Schreibkonsolidierung: Marker-Backfill und Mirror-Reparatur teilen sich
  pro Eintrag und Lauf genau einen `upsert_registry_entry()`-Aufruf.
- DECIDE 3: der Reconciler selbst ladet den Hub nie neu (reine Registry-
  /Dateisystem-Reparatur).
"""
import json

from mcp.installer_reconcile import reconcile_tool_manifest_mirrors
from mcp.installer_registry import MANAGED_BY_INSTALLER
from mcp.installer_tool_intents import build_tool_intent_mirror
from tests._tool_manifest_mirror_reconcile_helpers import (
    _bind_custom_mcps_dir,
    _bind_registry,
    _registry_entry,
    _write_bundle,
)


def test_reconcile_refreshes_mirror_on_hash_drift_for_already_marked_entry(monkeypatch, tmp_path):
    custom_dir = _bind_custom_mcps_dir(monkeypatch, tmp_path)
    bundle_dir = _write_bundle(custom_dir, "delta", [{"name": "old_tool", "description": "Old."}])
    old_mirror = build_tool_intent_mirror(bundle_dir / "tool_intents.json", bundle_version="1.0.0")
    registry_path = _bind_registry(
        monkeypatch,
        tmp_path,
        {"delta": _registry_entry(managed_by=MANAGED_BY_INSTALLER, tool_intents=old_mirror)},
    )

    # Bundle-Wahrheit aendert sich (z.B. durch manuelles Bearbeiten ausserhalb
    # des Installer-Lebenszyklus) - der Mirror in der Registry ist jetzt stale.
    (bundle_dir / "tool_intents.json").write_text(
        json.dumps({"schema_version": 1, "tools": [{"name": "new_tool", "description": "New."}]}),
        encoding="utf-8",
    )

    result = reconcile_tool_manifest_mirrors()

    assert result == {"changed": True, "repaired": ["delta"], "removed": [], "unresolved": []}
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    tool_names = {tool["name"] for tool in payload["delta"]["tool_intents"]["tools"]}
    assert tool_names == {"new_tool"}


def test_reconcile_clears_stale_mirror_and_persists_marker_backfill_when_bundle_invalid(
    monkeypatch, tmp_path
):
    # Codex Checkpoint 4 P1: ein invalides Bundle (kaputte tool_intents.json)
    # darf den alten Mirror nicht aktiv im Registry-Eintrag stehen lassen -
    # Fail-closed statt stale ("Bundle = Authoring Source"). Gleichzeitig
    # darf ein im selben Lauf gesetzter Marker-Backfill nicht verloren gehen,
    # nur weil der Mirror unresolved bleibt.
    custom_dir = _bind_custom_mcps_dir(monkeypatch, tmp_path)
    bundle_dir = _write_bundle(custom_dir, "epsilon", [{"name": "old_tool", "description": "Old."}])
    old_mirror = build_tool_intent_mirror(bundle_dir / "tool_intents.json", bundle_version="1.0.0")
    registry_path = _bind_registry(
        monkeypatch, tmp_path, {"epsilon": _registry_entry(managed_by=None, tool_intents=old_mirror)}
    )

    (bundle_dir / "tool_intents.json").write_text("not json", encoding="utf-8")

    result = reconcile_tool_manifest_mirrors()

    assert result == {
        "changed": True,
        "repaired": ["epsilon"],
        "removed": [],
        "unresolved": ["epsilon"],
    }
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["epsilon"]["managed_by"] == MANAGED_BY_INSTALLER
    assert payload["epsilon"]["tool_intents"] is None


def test_reconcile_writes_at_most_once_per_entry_when_backfilling_and_refreshing(
    monkeypatch, tmp_path
):
    # Marker-Backfill und Mirror-Reparatur muessen sich einen einzigen
    # upsert_registry_entry()-Aufruf teilen, nicht zwei separate Schreib-
    # zyklen ausloesen.
    custom_dir = _bind_custom_mcps_dir(monkeypatch, tmp_path)
    _write_bundle(custom_dir, "alpha", [{"name": "alpha_tool", "description": "Alpha."}])
    _bind_registry(monkeypatch, tmp_path, {"alpha": _registry_entry(tool_intents=None)})

    import mcp.installer_reconcile as installer_reconcile

    calls = []
    real_upsert = installer_reconcile.upsert_registry_entry

    def counting_upsert(name, config):
        calls.append(name)
        return real_upsert(name, config)

    monkeypatch.setattr(installer_reconcile, "upsert_registry_entry", counting_upsert)

    reconcile_tool_manifest_mirrors()

    assert calls == ["alpha"]


def test_reconcile_module_does_not_import_the_hub(monkeypatch, tmp_path):
    # Codex DECIDE 3: reine Registry-/Dateisystem-Reparatur. Der Reconciler
    # darf den Hub weder importieren noch (re-)laden - statische Pruefung des
    # Modul-Quelltexts, nicht nur Verhalten in diesem einen Testlauf.
    import inspect

    import mcp.installer_reconcile as installer_reconcile

    assert not hasattr(installer_reconcile, "get_hub")
    assert not hasattr(installer_reconcile, "reload_hub_registry")
    assert "mcp.hub" not in inspect.getsource(installer_reconcile.reconcile_tool_manifest_mirrors)
    assert "mcp.hub" not in inspect.getsource(installer_reconcile._reconcile_entry)
    assert "mcp.hub" not in inspect.getsource(installer_reconcile._refresh_mirror)

    _bind_custom_mcps_dir(monkeypatch, tmp_path)
    _bind_registry(monkeypatch, tmp_path, {})
    reconcile_tool_manifest_mirrors()
