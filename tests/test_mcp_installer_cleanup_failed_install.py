"""P11.0 SP3 - installer_install_routes._cleanup_failed_install() Rollback.

Herausgeloest aus tests/test_mcp_installer_route_wiring.py (Codex Checkpoint
4 P1: eigene Verantwortung, Doc 07s 200-Zeilen-Grenze). Tests fuer
delete_mcp() liegen in tests/test_mcp_installer_delete_mcp.py.

Deckt ab:
- Reihenfolge bindend, identisch zu delete_mcp() (SP3 Lifecycle-Invariante):
  Mirror entfernen -> Hub reload -> Bundle entfernen.
- Codex Checkpoint 4 P1: Loeschfehler werden geloggt statt mit
  `ignore_errors=True` verschluckt - aber dies ist ein Best-Effort-Rollback
  nach einem bereits fehlgeschlagenen Install, daher wird geloggt statt
  erneut geworfen (ein Crash hier wuerde die eigentliche, dem Nutzer
  gemeldete Fehlermeldung verdecken).
- Codex Checkpoint 4 P1 (3. Runde, widerruft die 2. Runde): die drei Stufen
  (Registry-Entfernen, Hub-Reload, Bundle-rmtree) sind ABHAENGIG, nicht
  unabhaengig. Die 2. Runde hatte noch verlangt, jede Stufe einzeln
  abzusichern, damit ein Fehler in einer Stufe die naechste nicht verhindert -
  das erzeugte aber genau die verbotenen Zustaende (Registry oder Hub-Cache
  zeigen auf ein bereits geloeschtes Bundle, wenn eine spaetere Stufe trotz
  Fehler in einer frueheren weiterlief). Scheitert remove_registry_entry()
  oder reload_hub_registry(), wird geloggt, das Bundle bleibt erhalten, und
  die Funktion stoppt - sie wirft dabei weiterhin nie selbst (Best-Effort-
  Rollback nach einem bereits fehlgeschlagenen Install, ein Crash hier wuerde
  die urspruengliche, dem Nutzer gemeldete Install-/Healthcheck-Fehlermeldung
  verdecken).
"""


def test_cleanup_failed_install_removes_registry_then_reloads_hub_before_deleting_bundle(
    monkeypatch, tmp_path
):
    # SP3 Lifecycle-Invariante (Rollback nach fehlgeschlagenem Healthcheck):
    # dieselbe Reihenfolge wie installer_manage_routes.delete_mcp() - Mirror
    # entfernen -> Hub reload -> Bundle entfernen. Der zweite Reload ist
    # bindend: ohne ihn haelt der Hub nach dem fehlgeschlagenen Healthcheck
    # weiterhin den bereits wieder entfernten Registry-Eintrag im Speicher
    # (er wurde vor dem Healthcheck einmal geladen, siehe install_mcp()).
    import mcp.installer_install_routes as install_routes

    target_dir = tmp_path / "demo"
    target_dir.mkdir()

    order = []
    monkeypatch.setattr(
        install_routes,
        "remove_registry_entry",
        lambda name: order.append(("remove_registry_entry", target_dir.exists())),
    )
    monkeypatch.setattr(
        install_routes,
        "reload_hub_registry",
        lambda hub: order.append(("reload_hub_registry", target_dir.exists())),
    )
    monkeypatch.setattr(install_routes, "get_hub", lambda: object())

    real_rmtree = install_routes.shutil.rmtree

    def tracking_rmtree(path):
        order.append(("rmtree", target_dir.exists()))
        real_rmtree(path)

    monkeypatch.setattr(install_routes.shutil, "rmtree", tracking_rmtree)

    install_routes._cleanup_failed_install("demo", target_dir)

    assert [step[0] for step in order] == ["remove_registry_entry", "reload_hub_registry", "rmtree"]
    assert order[0][1] is True
    assert order[1][1] is True
    assert not target_dir.exists()


def test_cleanup_failed_install_logs_instead_of_raising_when_rmtree_fails(monkeypatch, tmp_path, caplog):
    # Codex Checkpoint 4 P1: Loeschfehler muessen sichtbar werden (Logging),
    # duerfen aber die eigentliche, dem Nutzer gemeldete Installationsfehler-
    # Antwort nicht durch einen zusaetzlichen Crash verdecken - dies ist ein
    # Best-Effort-Rollback nach einem bereits fehlgeschlagenen Install.
    import logging

    import mcp.installer_install_routes as install_routes

    target_dir = tmp_path / "demo"
    target_dir.mkdir()

    monkeypatch.setattr(install_routes, "remove_registry_entry", lambda name: None)
    monkeypatch.setattr(install_routes, "reload_hub_registry", lambda hub: None)
    monkeypatch.setattr(install_routes, "get_hub", lambda: object())

    def boom(path):
        raise OSError("disk full")

    monkeypatch.setattr(install_routes.shutil, "rmtree", boom)

    with caplog.at_level(logging.ERROR):
        status = install_routes._cleanup_failed_install("demo", target_dir)  # darf nicht raisen

    assert target_dir.exists()
    assert any(record.levelno >= logging.ERROR for record in caplog.records)
    assert status["bundle_removed"] is False


def test_cleanup_failed_install_stops_and_keeps_bundle_when_registry_removal_fails(
    monkeypatch, tmp_path, caplog
):
    # Codex Checkpoint 4 P1 (3. Runde, widerruft die 2. Runde): scheitert
    # remove_registry_entry(), muss die Funktion stoppen - weder
    # reload_hub_registry() noch der Bundle-rmtree duerfen noch laufen, sonst
    # entstehen genau die verbotenen Zustaende (Registry/Hub-Cache zeigen auf
    # ein bereits geloeschtes Bundle). Das Bundle bleibt erhalten; die
    # Funktion wirft dabei weiterhin nie selbst.
    import logging

    import mcp.installer_install_routes as install_routes

    target_dir = tmp_path / "demo"
    target_dir.mkdir()

    reload_calls = []

    def boom(name):
        raise RuntimeError("registry write failed")

    monkeypatch.setattr(install_routes, "remove_registry_entry", boom)
    monkeypatch.setattr(
        install_routes, "reload_hub_registry", lambda hub: reload_calls.append(hub)
    )
    monkeypatch.setattr(install_routes, "get_hub", lambda: object())

    with caplog.at_level(logging.ERROR):
        status = install_routes._cleanup_failed_install("demo", target_dir)  # darf nicht raisen

    assert reload_calls == []
    assert target_dir.exists()
    assert status == {"registry_removed": False, "hub_reloaded": False, "bundle_removed": False}
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


def test_cleanup_failed_install_stops_and_keeps_bundle_when_hub_reload_fails(
    monkeypatch, tmp_path, caplog
):
    # Codex Checkpoint 4 P1 (3. Runde, widerruft die 2. Runde): scheitert
    # reload_hub_registry() (Registry-Entfernen war bereits erfolgreich),
    # muss die Funktion stoppen - der Bundle-rmtree darf nicht mehr laufen,
    # sonst zeigt der Hub-Cache moeglicherweise auf ein bereits geloeschtes
    # Bundle, falls der Reload selbst fehlschlaegt.
    import logging

    import mcp.installer_install_routes as install_routes

    target_dir = tmp_path / "demo"
    target_dir.mkdir()

    registry_calls = []

    def boom(hub):
        raise RuntimeError("hub reload failed")

    monkeypatch.setattr(
        install_routes, "remove_registry_entry", lambda name: registry_calls.append(name)
    )
    monkeypatch.setattr(install_routes, "reload_hub_registry", boom)
    monkeypatch.setattr(install_routes, "get_hub", lambda: object())

    with caplog.at_level(logging.ERROR):
        status = install_routes._cleanup_failed_install("demo", target_dir)  # darf nicht raisen

    assert registry_calls == ["demo"]
    assert target_dir.exists()
    assert status == {"registry_removed": True, "hub_reloaded": False, "bundle_removed": False}
    assert any(record.levelno >= logging.ERROR for record in caplog.records)
