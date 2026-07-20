"""P11.0 SP3 - mcp.installer_paths: zentrale MCP-ID-Validierung.

Codex Checkpoint 4 P0 (2. Runde): installer_manifest_normalize.py akzeptierte
MCP-IDs wie '../victim' ungeprueft; sie liefen ueber
installer_install_routes.py direkt in custom_mcp_dir() und konnten damit
schon bei der Installation aus custom_mcps/ ausbrechen. Zwei unabhaengige
Sicherungen, beide hier getestet:
1. validate_mcp_id() lehnt jedes Pfadsegment ab, das nicht buchstaeblich ein
   einzelner, sicherer Name ist (.., Separatoren, absolute Pfade, leer).
2. custom_mcp_dir() beweist zusaetzlich defensiv, dass der AUFGELOESTE
   Zielpfad direkt unter custom_mcps/ liegt - unabhaengig von (1), falls eine
   zukuenftige Aenderung an validate_mcp_id() eine Luecke uebersieht.
"""
import pytest
from fastapi import HTTPException

import mcp.installer_paths as installer_paths


@pytest.mark.parametrize(
    "bad_id",
    [
        "..",
        "../victim",
        "../../etc/passwd",
        "/etc/passwd",
        "a/b",
        "a\\b",
        "",
        ".",
    ],
)
def test_validate_mcp_id_rejects_unsafe_segments(bad_id):
    with pytest.raises(HTTPException) as exc_info:
        installer_paths.validate_mcp_id(bad_id)
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("good_id", ["time-mcp-test", "demo", "a.b.c", "demo_v2"])
def test_validate_mcp_id_accepts_single_safe_segments(good_id):
    assert installer_paths.validate_mcp_id(good_id) == good_id


def test_custom_mcp_dir_rejects_traversal_id_before_touching_disk(monkeypatch, tmp_path):
    # Belegt Codex' konkretes Beispiel: '../victim' darf niemals zu einem
    # Pfad ausserhalb von custom_mcps/ aufgeloest werden.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path / "custom_mcps"))
    victim = tmp_path / "victim"

    with pytest.raises(HTTPException):
        installer_paths.custom_mcp_dir("../victim")

    assert not victim.exists()


def test_custom_mcp_dir_proves_containment_independently_of_validate_mcp_id(monkeypatch, tmp_path):
    # Codex Checkpoint 4 P0 (2. Runde): custom_mcp_dir() muss defensiv
    # beweisen, dass der aufgeloeste Zielpfad direkt unter custom_mcps/
    # liegt - als ZWEITE, unabhaengige Sicherung, nicht nur als Folge von
    # validate_mcp_id(). Simuliert eine zukuenftige Luecke in
    # validate_mcp_id(), die ein '../victim' faelschlich durchliesse.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path / "custom_mcps"))
    monkeypatch.setattr(installer_paths, "validate_mcp_id", lambda name: name)

    with pytest.raises(HTTPException):
        installer_paths.custom_mcp_dir("../victim")


def test_custom_mcp_dir_accepts_safe_id_directly_under_root(monkeypatch, tmp_path):
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path / "custom_mcps"))

    result = installer_paths.custom_mcp_dir("time-mcp-test")

    assert result.parent == (tmp_path / "custom_mcps").resolve()
    assert result.name == "time-mcp-test"


def test_resolve_icon_path_still_rejects_paths_outside_bundle_dir(monkeypatch, tmp_path):
    # Bestehender Vertrag (resolve_icon_path nutzt custom_mcp_dir() intern)
    # bleibt nach Split/Haertung unveraendert: ein Icon-Pfad ausserhalb des
    # Bundle-Verzeichnisses liefert weiterhin None statt eines Pfads.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path / "custom_mcps"))
    bundle_dir = installer_paths.custom_mcps_dir() / "demo"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "icon.svg").write_text("<svg/>", encoding="utf-8")

    safe = installer_paths.resolve_icon_path("demo", {"ui": {"icon": "icon.svg"}})
    unsafe = installer_paths.resolve_icon_path("demo", {"ui": {"icon": "../../escape.svg"}})

    assert safe is not None and safe.name == "icon.svg"
    assert unsafe is None


def test_resolve_icon_path_rejects_name_prefixed_sibling_directory(monkeypatch, tmp_path):
    # Codex Checkpoint 4 P0 (3. Runde), Codex' konkretes Beispiel: Bundle
    # "demo", Icon "../demo-secrets/secret.svg". Der aufgeloeste Pfad ist
    # .../custom_mcps/demo-secrets/secret.svg - als ZEICHENKETTE beginnt das
    # mit str(root) == ".../custom_mcps/demo", weil "demo-secrets" als String
    # mit "demo" beginnt. `str.startswith` haette das faelschlich als
    # "innerhalb des Bundles" akzeptiert, obwohl demo-secrets ein voellig
    # eigenstaendiges Nachbarverzeichnis ist. Die echte Pfadbeziehung
    # (root in candidate.parents) muss das ablehnen.
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path / "custom_mcps"))
    bundle_dir = installer_paths.custom_mcps_dir() / "demo"
    bundle_dir.mkdir(parents=True)
    secret_dir = installer_paths.custom_mcps_dir() / "demo-secrets"
    secret_dir.mkdir(parents=True)
    (secret_dir / "secret.svg").write_text("<svg/>", encoding="utf-8")

    escaped = installer_paths.resolve_icon_path(
        "demo", {"ui": {"icon": "../demo-secrets/secret.svg"}}
    )

    assert escaped is None
