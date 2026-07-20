---
scope: layer_prompt
target: control_verify_input
variables: ["verifier_input_json"]
status: active
---

VERIFY-INPUT:
{verifier_input_json}

Bei `document_mode="long_document"` bewerte die Anfrage anhand von Summary und
Dokument-Metadaten. Nimm NICHT stillschweigend an, dass der komplette Rohtext
im Prompt vorliegt.
Pruefe dokumentbezogene Retrieval-Plaene besonders darauf, ob der gewaehlte
Retrieval-Modus, bekannte `workspace_entry_ids` und strukturierte Kandidaten
zum vorgeschlagenen Leseplan passen.

Wenn `document_retrieval.retrieval_mode` vorhanden ist, klassifiziere die
Anfrage zuerst nach diesem Modus, bevor du entscheidest, welche Evidenz
erforderlich ist.
Wenn `document_retrieval.question_focus` vorhanden ist, nutze dieses Signal
vorrangig fuer die Einordnung von Inhaltsfrage vs. Strukturfrage vs.
Exact-Lookup. Wenn `structure_required=true`, behandle die Frage als
strukturabhaengig.

SEMANTIC-FIRST INPUT:
- Behandle die Anfrage als Inhalts- oder Bedeutungsfrage, solange der User
  nicht explizit nach Kapitelanzahl, Abschnittsreihenfolge,
  Inhaltsverzeichnis, Dokumentstruktur, exaktem Zitat, exakter Passage,
  exaktem Eintrag oder exakter Position fragt.
- Typische semantic-first Fragen sind Formulierungen wie:
  `Was passiert in X?`, `Worum geht es in X?`, `Warum passiert X?`,
  `Wer macht X?`, `Wie verhaelt sich X zu Y?`
- Pruefe bei semantischen Fragen, ob die vorhandenen Signale genuegen, um die
  tatsaechliche Inhaltsfrage zu beantworten.
- Primaere Signale: `document_retrieval.semantic_keys`,
  `document_retrieval.preferred_entry_ids` und passende abgerufene Inhalte.
- Sekundaere Signale: `document_retrieval.index_like_entry_ids` und
  `document_retrieval.chapter_candidate_entry_ids`.
- Downgrade, Reject oder Redirect eine semantische Anfrage NICHT nur deshalb,
  weil Kapitel- oder Index-Abdeckung unvollstaendig ist, solange die
  semantische Evidenz selbst ausreicht.
- Wenn eine semantische Anfrage einen Kapitel- oder Abschnittsnamen nennt
  wie `Was passiert in PREGO!?`, bleibt sie trotzdem semantic-first, solange
  der User nach Inhalt statt nach Struktur dieses Kapitels fragt.

STRUCTURE-FIRST INPUT:
- Verlange bei Strukturfragen Evidenz fuer Kapitel, Abschnitte, Reihenfolge,
  Ueberschriften, Inhaltsverzeichnis oder Strukturabdeckung.
- Nutze `document_retrieval.index_like_entry_ids` und
  `document_retrieval.chapter_candidate_entry_ids` als primaere Signale.
- Typische structure-first Fragen sind Formulierungen wie:
  `Wie viele Kapitel hat das Dokument?`, `In welcher Reihenfolge stehen die
  Abschnitte?`, `Gibt es ein Inhaltsverzeichnis?`

EXACT-LOOKUP / WORKSPACE-FIRST INPUT:
- Verlange bei exakten Lookup-Fragen direkte Abdeckung des angefragten Textes,
  Eintrags oder Workspace-Ziels.
- Nutze `document_retrieval.workspace_entry_ids` und
  `document_retrieval.preferred_entry_ids` als primaere Signale.
- Verlange Revision oder Klaerung, wenn das exakte Ziel nicht identifizierbar
  oder nicht abgedeckt ist.
