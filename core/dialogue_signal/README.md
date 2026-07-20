# Dialogue Signal

Kleine Hilfsschicht fuer Interaktionsart und Antwortton.

Liefert nur:
- `dialogue_act`
- `response_tone`
- `response_length_hint`
- `confidence`

Sie liefert **keine** Tool-Wahrheit und **keine** Evidence.

Verwendung:
- Thinking darf damit soziale/reflektierende Turns von Runtime-Requests trennen.
- Output darf damit Ton und Laenge steuern.
- Capability-Resolver, Evidence-Guard und Tool-Executor bleiben davon fachlich getrennt.
