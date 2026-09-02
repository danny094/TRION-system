---
id: system-auth-model
title: Auth-Modell im TRION-System
scope: auth_model
tags:
  - auth
  - token
  - credentials
  - secrets
  - bearer
  - zugriff
priority: 80
retrieval_hints:
  - auth
  - token
  - credentials
  - zugriff
  - bearer
  - secret resolve
  - zugriffsmodell
  - wie authentifiziere
  - interner token
confidence: high
last_reviewed: 2026-09-01
---

## Invarianten

- Auth-Regel != Live-Konfiguration.
- Diese Datei beschreibt Zugriffsmodell, nicht aktuelle Reachability.
- Secret-Werte sind nie ausgabefähig.
- Docker- oder Hostnetz-Naehe erzeugt keinen Principal.
- Vor dem Router wird jeder Admin-API-Caller authentisiert, ausser
  `GET /health` und der provisionierte `POST /api/auth/login`. Unprovisionierter
  Login wird bereits in der Middleware vor der Bodyvalidierung blockiert.
- Resolve-sensitive Endpoints sind nicht als externe Standardpfade zu behandeln.

## Auth-Zonen

| zone | regel |
|---|---|
| browser_session | signiertes `HttpOnly`-/`SameSite=Strict`-Cookie; Mutation zusaetzlich Origin und CSRF |
| token_guarded_secret_resolve | eigener Secret-Datei-Bearer nur fuer den Resolve-GET |
| token_guarded_memory_read | getrennter Secret-Datei-Bearer nur fuer drei Settings-/Routing-GETs |
| plugin_delegation | nur der von der Middleware verifizierte Browserbeleg wird weitergereicht |
| proxy_exposed | WebUI same-origin `/api`; WebUI/Admin nur loopback, Memory ohne Hostport |
| tool_guarded_access | operative Nutzung bevorzugt über Tools statt rohe Direktcalls |

## Secret-Endpoints

| endpoint | auth | netzregel | ausgabe |
|---|---|---|---|
| `POST /api/auth/login` | installiertes lokales Credential | loopback/same-origin | Session-Cookie + feste Metadaten |
| `GET /api/auth/session` | gueltiges Session-Cookie | loopback/same-origin | Principal, Ablauf, CSRF |
| `POST /api/auth/logout` | Session + Origin + CSRF | loopback/same-origin | widerruft Sessiongeneration |
| `GET /api/secrets` | Browser-Session | loopback/same-origin | nur Namen |
| `GET /api/secrets/resolve/{NAME}` | route-spezifischer Bearer aus Secret-Datei | Docker-Netz, nicht normaler Browserpfad | Klartext-Secret |
| drei Memory-Settings-/Routing-GETs | getrennter Memory-Read-Bearer aus Secret-Datei | Docker-Netz | nicht geheime Konfiguration |
| Admin-API → MCP `secret_save` | interner Call | Docker-Netz | persistiert verschlüsselt |

## Allgemeine Regeln

- Die Admin-Middleware ist die einzige technische Principal-Verifikation vor
  den Routern; fehlendes Bootstrap-Material blockiert ausser `/health`.
- Secret-Resolve und Memory-Read verwenden getrennte, route-spezifische Tokens
  aus read-only Secret-Dateien ohne ENV-/`.env`-Fallback.
- Resolve-Endpoint ist sensitiv, auch wenn Name bekannt ist.
- Secret-Namen sind weniger sensitiv als Secret-Werte, aber nicht frei publizierbar.

## Browser und Plugins

- `AuthGate` umschliesst die WebUI-Shell und konsumiert Login, Sessionstatus
  und Logout ueber den zentralen same-origin API-Client.
- Browsermutationen brauchen den sessiongebundenen Header `x-csrf-token` und
  eine erlaubte lokale Origin.
- Installierbare Plugins laufen in SP1 ausschliesslich als
  `OPAQUE_IFRAME_ONLY` ohne Browser-Session; same-origin ESM bleibt blockiert.
- Die authentisierte Parent-Mediation ist bis P16-SP4 nicht aktiv. Ihr
  gespeicherter Backend-Bridgevertrag besitzt kein Service-Secret und darf
  spaeter ausschliesslich serverseitig verifizierte Delegationsheader nutzen.
- Plugin-Payloads koennen Cookie, Authorization, Origin oder CSRF weder setzen
  noch einen serverseitig verifizierten Wert ueberschreiben.

## Skill-Regeln

- Skills sollen Secrets über `get_secret("NAME")` beziehen.
- `get_secret("NAME")` kapselt Namensnormalisierung, Resolve und Alias-Fallback.
- Skill-Code soll keine Secret-Werte hardcoden.
- Skill-Code soll keine Secret-Werte aus normalen Dateien oder freier Env lesen.
- Skill-Code soll Secret-Werte nicht loggen, nicht printen, nicht zurückgeben.

## Nie nach außen geben

- Secret-Werte
- Bearer-Token für Secret-Resolve oder Memory-Read
- Authorization-Header
- API-Key-Strings
- Klartext-Secrets in Tool-Trace
- Klartext-Secrets in Chat-Antworten
- Klartext-Secrets in Exceptions oder Debug-Logs

## Offen vs. intern

| bereich | außen_geeignet | intern_only |
|---|---|---|
| normale UI/API-Nutzung | ja | nein |
| Secret-Namen listing | eingeschränkt | bevorzugt intern |
| Secret-Klartext resolve | nein | ja |
| operative Secret-Nutzung | nein | ja |
| rohe interne Resolve-URLs als Nutzerpfad | nein | ja |

## Zugriff

- Für Secret-Verwendung in Skills: `get_secret("NAME")`.
- Für Secret-Inventar: `GET /api/secrets` oder entsprechende interne Tool-Pfade.
- Für Klartext-Resolve: nur intern, nur mit dem route-spezifischen
  Secret-Datei-Bearer und nur wenn operativ nötig.
- Für normale Agentenentscheidungen erst read-only Pfade bevorzugen.

## Grenzen

- Status: kein aktueller Runtime-PASS; diese Datei ist nur statischer Vertrag.
- Diese Datei sagt nicht, ob ein Token aktuell gesetzt ist.
- Diese Datei sagt nicht, ob nginx aktuell einen Pfad exponiert.
- Diese Datei sagt nicht, ob ein Endpoint aktuell erreichbar ist.
- Diese Datei erlaubt nie die Ausgabe von Secret-Werten.
