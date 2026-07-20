---
scope: layer_prompt
target: thinking_document_context
variables: ["document_context_summary"]
status: active
---

DOKUMENT-KONTEXT:
{document_context_summary}

Nutze bei langen Dokumenten bevorzugt die Chunk-Pointer und Retrieval-Schritte,
statt das gesamte Dokument implizit als Volltext anzunehmen.
