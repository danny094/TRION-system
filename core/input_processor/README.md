# Input Processor

Bereitet sehr lange User-Inputs fuer den Core auf, bevor Thinking damit plant.

**Einzige Aufgabe:** lange Dokument-Inputs als eigenen Pfad behandeln, ohne den
normalen Chat-Pfad zu veraendern.

---

## Status

- ✅ `contracts.py` implementiert
- ✅ `detect.py` erkennt Long-Document-Inputs deterministisch
- ✅ `chunker.py` schneidet Dokumente in ueberlappende Chunks
- ✅ `storage.py` kapselt Hook-basierte Workspace-/Semantic-Ablage
- ✅ `processor.py` verdrahtet nur Chunking, Storage und Summary
- ✅ `summarizer.py` erzeugt einen kleinen `DocumentContext` fuer den Planning-Pfad
- ✅ `DocumentContext` traegt jetzt strukturierte Retrieval-Hinweise wie `preferred_entry_ids` und `index_like_entry_ids`
- ✅ Thinking bekommt jetzt einen eigenen `document_context`-Prompt-Block
- ✅ Chunk-Pointer koennen im Planner fuer erste Retrieval-Schritte genutzt werden
- ✅ produktive Tool-Verfuegbarkeit fuer den Dokumentpfad kann jetzt ueber `core/pipeline/document_tools_stage.py` eingespeist werden
- ✅ dokumentbezogene Toolreihenfolge wird jetzt ueber Intent-Signale verfeinert
- ✅ Strukturfragen koennen jetzt bevorzugt gegen Inhaltsverzeichnis-/Kapitel-Kandidaten planen statt gegen einzelne harte Chunk-Annahmen
- ✅ semantische Dokument-Chunks tragen jetzt die zugehoerige `workspace_entry_id` fuer spaetere Read-Schritte mit
- ✅ spaetere `workspace_get`-Schritte koennen jetzt produktiv aus semantischen Treffern statt nur aus statischen Kandidatenlisten aufgeloest werden

---

## Modulstruktur

```text
core/input_processor/
├── contracts.py   ← DocumentChunk, DocumentContext
├── detect.py      ← Long-Document-Erkennung
├── chunker.py     ← Chunk-Schnitt mit Overlap
├── storage.py     ← Hook-basierte Workspace-/Semantic-Ablage
├── summarizer.py  ← deterministische Summary + Key Facts
└── processor.py   ← nur Verdrahtung der Input-Processor-Bausteine
```

---

## Regeln

- kein Import aus `memory/` oder `adapters/`
- Storage nur ueber injizierte Hooks
- keine LLM-Calls in diesem Modul
- normale Chat-Inputs bleiben unangetastet
- `processor.py` enthaelt keine Storage-Details

---

## Output

```python
DocumentContext(
    summary="...",
    key_facts=["..."],
    total_chunks=3,
    workspace_entry_ids=[101, 102, 103],
    preferred_entry_ids=[101, 102],
    index_like_entry_ids=[101],
    chapter_candidate_entry_ids=[101, 102],
    original_char_count=12840,
    semantic_keys=["document_chunk_0", "document_chunk_1", "document_chunk_2"],
    semantic_candidate_keys=["document_chunk_0", "document_chunk_1"],
)
```
