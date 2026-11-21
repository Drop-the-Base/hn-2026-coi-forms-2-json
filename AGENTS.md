# Zasady dla agentów - zespół H-kwadrat

## Workflow (dwa zespoły agentów)

Na tym repo pracują równolegle dwa zespoły. Źródłem prawdy o zadaniach są **GitHub Issues**.

| Zespół | Etykieta | Kto przypisuje |
| --- | --- | --- |
| Hermes (Ben) | `team:hermes` | konto benhus8 |
| Jakub | `team:Hudziak` | konto kolegi |

### Branie zadań
1. Wolne issue = otwarte, **bez assignee** i **bez etykiety `team:*`**. Tylko takie wolno brać.
2. Zgarnięcie: przypisz się i dodaj etykietę swojego zespołu, potem krótki komentarz, że bierzesz:
   `gh issue edit <N> --add-assignee @me --add-label "team:<twoj-zespol>"`
3. Sprawdź jeszcze raz (`gh issue view <N> --json assignees,labels`). Jeśli drugi zespół też się przypisał, wycofaj się i zostaw komentarz.
4. Issue z cudzą etykietą `team:*` jest zajęte. Nie ruszaj go, nie komentuj, nie zamykaj.
5. Nie bierz na zapas: tyle, ile zrobisz w najbliższej godzinie.

### Praca
- Branch: `<kto>/<nr issue>-<krotka-nazwa>`, np. `jarek/12-sortowanie`.
- PR z `Closes #<nr>` w opisie. Nie pushuj bezpośrednio na `main`.
- Duże issue możesz podzielić na mniejsze issues z dopiskiem `Część #<nr>`, z etykietą swojego zespołu.
- Przed merge'em: zielone testy. Konflikt z PR-em drugiego zespołu rozwiązuje ten, kto merguje później.

## Pisanie kodu
- Przy każdym zadaniu z kodem stosuj skill **ponytail** na poziomie `full` ([.claude/skills/ponytail/SKILL.md](.claude/skills/ponytail/SKILL.md)). Przegląd zmian: `ponytail-review`, audyt repo: `ponytail-audit`.

_Reszta do uzupełnienia (konwencje, styl, testy)._
