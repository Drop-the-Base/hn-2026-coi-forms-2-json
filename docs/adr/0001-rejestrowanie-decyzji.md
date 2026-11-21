# ADR-0001: Rejestrujemy decyzje w ADR

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-10

## Kontekst

Na repo pracują równolegle dwie osoby i dwa agenty. Agent nie pamięta wcześniejszych rozmów, więc decyzje muszą być zapisane w repo. Jury ocenia dokumentację architektury (Z 3.2.II).

## Decyzja

Każda decyzja o technologii lub wzorcu trafia do `docs/adr/` według szablonu z [README](README.md). Agent przed dodaniem zależności sprawdza rejestr ADR i [politykę licencji](0013-polityka-licencji.md).

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Decyzje tylko w opisach PR | nie da się ich przeszukać, agent ich nie widzi |
| Jeden duży plik z decyzjami | konflikty przy równoległej pracy dwóch agentów |

## Konsekwencje

Każdy PR z nową zależnością jest trochę większy. W zamian nikt nie wybiera biblioteki drugi raz ani nie dodaje zakazanej licencji.
