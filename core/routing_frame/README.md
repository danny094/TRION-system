# Routing Frame

Gemeinsame Schicht fuer den produktiven Routing-Vertrag.

Diese Schicht:

- sammelt vorhandene Routing-Signale
- normalisiert sie in einen `RoutingFrame`
- konsumiert occurrence-genau kartierte TMR-Projektionen

P11 SP8 R5: `build_routing_frame()` reicht `RawSignals.meaning` genau einmal
an `meaning_signal_projection_loader.project_meaning_signals`. Nur
occurrence-genau kartierte, eindeutige Predicate-/Theme-Paare mit belegter
Konfidenz duerfen Domain, Intent oder Evidence setzen. Alle anderen TMR-Felder
bleiben sanitisiertes `meaning_shadow_trace`; TMR waehlt kein Tool und setzt
keine Safety-/Eligibility-Regel. Ein Fehler im TMR-Aufbau oder eine
mehrdeutige/niedrig-konfidente Bedeutung bleibt fail-closed ohne Projektion.

Public architecture references:

- [Architecture](../../docs/architecture.md)
- [TRION Meaning Representation](../../tmr_concept.md)
- [Operation Contract](../../operation_contract_concept.md)
