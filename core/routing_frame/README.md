# Routing Frame

Shadow-Mode-Schicht fuer den geplanten gemeinsamen Routing-Vertrag.

Diese Schicht:

- sammelt vorhandene Routing-Signale
- normalisiert sie in einen `RoutingFrame`
- trifft noch keine produktive Umschaltung

P11 SP1: `RawSignals.meaning` (TRION Meaning Representation, TMR) ist ein
zusaetzliches Shadow-Feld (`core/routing_frame/meaning.py`,
`meaning_signals.py`, `meaning_shadow_trace.py`). Es ist nicht autoritativ:
`build_routing_frame()` spiegelt es nur sanitisiert nach
`source_signals["meaning_shadow_trace"]` (reine Diagnose, kein Doc-10-Event —
das ist SP7). Keine der Entscheidungs-Ableitungen (intent_kind, domain,
evidence_need, execution_mode, requested_operation_family, reasons) liest
`raw.meaning` — Routing und Toolwahl bleiben unveraendert (Doc55 A10). Ein
Fehler im TMR-Aufbau blockiert die Pipeline nicht
(`signal_collector._build_meaning_signal_safely` faengt ab).

Fuehrende Docs:

- [docs/routing/41-routing-ist-zustand.md](/Users/denniskassner/Documents/TRION-github/docs/routing/41-routing-ist-zustand.md)
- [docs/routing/42-routing-frame-v1.md](/Users/denniskassner/Documents/TRION-github/docs/routing/42-routing-frame-v1.md)
- [docs/architecture/55-trion-meaning-representation.md](/Users/denniskassner/Documents/TRION-github/docs/architecture/55-trion-meaning-representation.md)
