---
scope: layer_prompt
target: control_verify_plan
variables: ["plan_json"]
status: active
---

THINKING-PLAN:
{plan_json}

Pruefe, ob der Plan zur Anfrage passt, ob wesentliche Schritte fehlen und ob
die Ausfuehrung gegen erkennbare Safety-Regeln verstoesst.

Wenn der Plan Document-Retrieval nutzt, bewerte ihn auch danach, ob er zum
`document_retrieval.retrieval_mode` passt.
Wenn `document_retrieval.question_focus` vorhanden ist, nutze dieses Signal
als harte Leitplanke fuer die Hauptbewertung des Plans. Wenn
`structure_required=true`, darf der Plan Strukturabdeckung explizit
priorisieren.

SEMANTIC-FIRST PLAN:
- Approve nur, wenn die primaeren Schritte zur semantischen Inhaltsfrage des
  Users passen.
- Ein guter semantic-first Plan beantwortet die eigentliche Frage direkt, nutzt
  semantische Retrieval-Evidenz als Hauptgrundlage und behandelt
  Kapitel-/Index-/TOC-Signale nur als Navigationshilfen.
- Ein schwacher semantic-first Plan verschiebt den Fokus auf Kapitelzaehlung,
  TOC-Validierung, Outline-Rekonstruktion oder Strukturpruefung, obwohl der
  User nach Inhalt, Ereignissen, Beziehungen, Claims oder Erklaerung fragt.
- Verlange Revision, wenn der Hauptfokus des Plans auf Dokumentstruktur statt
  auf der angefragten Inhaltsbedeutung liegt.
- Wenn ein semantischer Plan inhaltlich passt, formuliere Warnings ebenfalls
  entlang der Inhaltsfrage. Kritisiere NICHT primaer fehlende Kapitel-,
  TOC- oder Index-Abdeckung, solange diese Strukturabdeckung fuer die
  Beantwortung der Inhaltsfrage nicht erforderlich ist.

SEMANTIC-FIRST EXAMPLES:
- Positiv:
  User fragt `Was passiert in PREGO!?`
  und der Plan sucht semantisch nach `PREGO`, liest passende Treffer und
  bewertet den Inhalt dieses Abschnitts. TOC- oder Kapitel-Signale duerfen nur
  als Navigationshilfe erwaehnt werden.
- Negativ:
  User fragt `Was passiert in PREGO!?`
  und der Plan oder die Warnings konzentrieren sich hauptsaechlich auf
  Kapitelanzahl, TOC-Vollstaendigkeit oder Strukturvalidierung statt auf den
  Inhalt von `PREGO`.

STRUCTURE-FIRST PLAN:
- Approve nur, wenn der Plan fuer Strukturfragen auch strukturelle Abdeckung
  prueft.
- Ein guter structure-first Plan validiert Kapitel, Abschnitte, Reihenfolge,
  Ueberschriften, TOC-/Index-Eintraege oder Vollstaendigkeit.
- Nutze `index_like_entry_ids` und `chapter_candidate_entry_ids` hier als
  primaere Evidenz.
- Bei structure-first duerven Warnings oder Revisionen ausdruecklich fehlende
  TOC-, Kapitel- oder Strukturabdeckung kritisieren, wenn genau diese Evidenz
  fuer die Userfrage noetig ist.

STRUCTURE-FIRST EXAMPLE:
- Positiv:
  User fragt `Wie viele Kapitel hat diese Geschichte?`
  und der Plan prueft Inhaltsverzeichnis, Kapitelkandidaten oder
  Struktur-Chunks, um die Kapitelanzahl zu validieren.

EXACT-LOOKUP / WORKSPACE-FIRST PLAN:
- Approve nur, wenn der Plan exakte Abdeckung des angefragten Eintrags, Zitats,
  Ausschnitts oder Workspace-Ziels prueft.
- Nutze `workspace_entry_ids` und `preferred_entry_ids` hier als primaere
  Evidenz.
- Verlange Revision, wenn der Plan exakte Abdeckung durch ungefaehre
  semantische Inferenz ersetzt.

DECISION RULE: RETRIEVAL MODE MISMATCH
- Wenn der Plan sicher ist, aber schlecht zum Retrieval-Modus passt, hard-blocke
  NICHT.
- Verwende `REJECTED`, wenn der Plan ueberarbeitet werden soll, um besser zur
  Userabsicht oder zum Retrieval-Modus zu passen.
- Verwende `APPROVED` nur, wenn die Haupt-Evidenzstrategie zum Retrieval-Modus
  passt.
- Verwende `HARD_BLOCK` nur bei Safety-, Policy-, Permission- oder
  Dangerous-Action-Verstoessen.
- Ein semantischer Plan mit korrekter Hauptstrategie bleibt `APPROVED`, auch
  wenn Strukturhilfen unvollstaendig sind. Nutze in diesem Fall hoechstens
  gezielte semantische Warnings statt strukturzentrierter Kritik.
