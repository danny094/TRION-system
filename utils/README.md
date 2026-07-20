# Utils

Geteilte Hilfsfunktionen die von mehreren Modulen gebraucht werden.
Kein Business-Logic — nur technische Werkzeuge.

---

## Struktur

```
utils/
├── logger.py                  ← Logging
├── json_parser.py             ← Compat-Shim → utils/text/json_parser.py
├── role_endpoint_resolver.py  ← Compat-Shim → utils/routing/role_endpoint.py
├── service_endpoint_resolver.py ← Compat-Shim → utils/routing/service_endpoint.py
├── ollama.py                  ← Ollama HTTP-Hilfsfunktionen
├── ollama_endpoint_manager.py ← Multi-Endpunkt-Fallback
├── text/
│   ├── json_parser.py         ← safe_parse_json()
│   ├── chunker.py             ← Text-Chunking
│   └── prompt.py              ← Prompt-Hilfsfunktionen
├── routing/
│   ├── role_endpoint.py       ← Ollama-Endpunkt pro Rolle auflösen
│   ├── service_endpoint.py    ← Service-Endpunkte auflösen
│   ├── ollama_manager.py      ← Ollama-Instanz-Management
│   └── model_runtime.py       ← Modell-Runtime-Auflösung
├── embedding/
│   ├── resolver.py            ← Embedding-Endpunkt auflösen
│   ├── health.py              ← Embedding-Service Health-Check
│   └── metrics.py             ← Embedding-Metriken
└── settings/
    ├── manager.py             ← Settings lesen/schreiben
    └── model.py               ← Settings-Datenmodell
```

---

## Wichtige Dateien

### `logger.py`
Einheitliches Logging für das gesamte TRION-System.
Stellt `log_info()`, `log_error()`, `log_warning()`, `log_debug()` bereit.
Kein direktes `print()` oder `logging.getLogger()` im restlichen Code.

### `text/json_parser.py`
Sicheres JSON-Parsing mit Fallback — wirft nie eine Exception.
`safe_parse_json(text, default, context)` → gibt immer `default` zurück wenn Parsing fehlschlägt.

### `routing/role_endpoint.py`
Löst für eine Rolle (`thinking`, `control`, `output`) den passenden Ollama-Endpunkt auf.
Inkl. Fallback-Logik, Health-Check und Caching.

### `routing/service_endpoint.py`
Löst externe Service-Endpunkte auf (container-commander, storage-broker, etc.).

### `embedding/resolver.py`
Bestimmt welcher Embedding-Endpunkt genutzt wird (GPU/CPU/Remote).

### `settings/manager.py`
Liest und schreibt persistente Settings (z.B. über Admin-API).

---

## Regeln

- **Kein Import aus `core/`** — utils kennt die Pipeline nicht
- **Kein Import aus `mcp/`** — utils ist die unterste Schicht
- **Keine Business-Logic** — nur technische Werkzeuge
- **Alle Funktionen sind pure** — kein globaler State außer in `logger.py`
- **Max 150 Zeilen pro Datei**
