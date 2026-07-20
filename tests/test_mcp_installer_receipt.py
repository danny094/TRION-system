"""P11.0 SP3 - mcp.installer_receipt: Receipt-Aufbau und Pfad-Validierung.

`test_build_install_receipt_tracks_owned_paths` wurde aus
tests/test_mcp_installer_manifest.py hierher verschoben (eigene fachliche
Verantwortung: Receipt-Vertrag statt Archiv-Extraktion/Manifest-Normalisierung
- und Doc 07s 200-Zeilen-Grenze).

Deckt ab:
- Codex Checkpoint 4 P1: der Receipt speichert nur einen Mirror-Hash, keine
  zweite, stale Kopie der vollen `tool_intents`.
- Codex Checkpoint 4 P0: `owned_paths_from_receipt()` liefert nur Pfade, die
  nachweislich zum erwarteten Bundle gehoeren - ein manipuliertes Receipt
  (fremder `mcp_id`, oder `owned_paths` ausserhalb des Bundle-Verzeichnisses)
  darf nichts liefern, das spaeter an `shutil.rmtree()` geht.

Routen-Ebene (delete_mcp() nutzt owned_paths_from_receipt() end-to-end) wird
in tests/test_mcp_installer_delete_mcp.py abgedeckt - hier: reine
Unit-Vertraege der Receipt-Funktionen selbst.
"""
import json

from mcp.installer_receipt import build_install_receipt, owned_paths_from_receipt


def test_build_install_receipt_tracks_owned_paths(tmp_path):
    target_dir = tmp_path / "time-mcp-test"
    registry_path = tmp_path / "mcp_registry.json"
    receipt = build_install_receipt(
        "time-mcp-test",
        {
            "version": "1.0.0",
            "manifest_format": "mcp.json",
            "ui": {"icon": "assets/icon.svg"},
            "plugin": {"required": False},
        },
        target_dir,
        registry_path,
    )

    assert receipt["mcp_id"] == "time-mcp-test"
    assert receipt["version"] == "1.0.0"
    assert receipt["owned_paths"] == [str(target_dir)]
    assert receipt["registry_paths"] == [str(registry_path)]


def test_build_install_receipt_stores_mirror_hash_not_full_tool_intents_copy(tmp_path):
    # Codex Checkpoint 4 P1: der Receipt darf keine zweite, stale Kopie der
    # vollen tool_intents-Mirror-Struktur speichern - nur den Hash, der schon
    # im bereits gebauten Mirror steckt (eine Quelle fuer den Wert).
    target_dir = tmp_path / "time-mcp-test"
    registry_path = tmp_path / "mcp_registry.json"
    mirror = {
        "schema_version": 1,
        "source_sha256": "deadbeef" * 8,
        "bundle_version": "1.0.0",
        "tools": [{"name": "time_now", "description": "Return time."}],
    }
    receipt = build_install_receipt(
        "time-mcp-test",
        {"version": "1.0.0", "manifest_format": "mcp.json", "tool_intents": mirror},
        target_dir,
        registry_path,
    )

    assert receipt["tool_intents_hash"] == mirror["source_sha256"]
    assert "tool_intents" not in receipt
    # Der Receipt darf nicht zusaetzlich die volle tools-Liste duplizieren.
    serialized = json.dumps(receipt)
    assert "time_now" not in serialized


def test_owned_paths_from_receipt_rejects_mismatched_mcp_id(tmp_path):
    # Codex Checkpoint 4 P0: ein Receipt mit fremder mcp_id darf keine Pfade
    # liefern, auch wenn die Pfade selbst plausibel aussehen.
    target_dir = tmp_path / "demo"
    target_dir.mkdir()
    (target_dir / ".trion-install.json").write_text(
        json.dumps({"mcp_id": "other-mcp", "owned_paths": [str(target_dir)]}), encoding="utf-8"
    )

    try:
        owned_paths_from_receipt("demo", target_dir)
        assert False, "expected ValueError for mismatched mcp_id"
    except ValueError:
        pass


def test_owned_paths_from_receipt_ignores_paths_outside_target_dir(tmp_path):
    # Codex Checkpoint 4 P0: owned_paths_from_receipt() darf manipulierte
    # Pfade ausserhalb des erwarteten Bundle-Verzeichnisses nicht liefern -
    # diese Pfade landen sonst ungeprueft in shutil.rmtree().
    target_dir = tmp_path / "demo"
    target_dir.mkdir()
    victim_dir = tmp_path / "victim"
    victim_dir.mkdir()
    inside_path = target_dir / "data"
    inside_path.mkdir()
    (target_dir / ".trion-install.json").write_text(
        json.dumps(
            {
                "mcp_id": "demo",
                "owned_paths": [str(victim_dir), str(inside_path), str(target_dir)],
            }
        ),
        encoding="utf-8",
    )

    result = owned_paths_from_receipt("demo", target_dir)

    assert victim_dir.resolve() not in result
    assert inside_path.resolve() in result
    assert target_dir.resolve() in result
