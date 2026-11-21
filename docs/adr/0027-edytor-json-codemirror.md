# ADR-0027: Edytor JSON na ekranie przeglądu: pakiety CodeMirror 6

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-T1, FR-T2, FR-E4, FR-E5, NFR-15

## Kontekst

Ekran przeglądu (#52, #54, makieta [przeglad.html](../../frontend/design/przeglad.html)) potrzebuje edytora JSON: numery linii, przejście do elementu po ścieżce z wyniku (`tabs[1].questions[0].field…`), podświetlenie linii bieżącego elementu, znacznik pewności w rynnie, błędy z linią, „Formatuj” z cofaniem. [ADR-0011](0011-frontend-react-vite.md) wskazał CodeMirror 6 bez listy pakietów i licencji. Wynik formularza ma 800–3000 linii.

## Decyzja

CodeMirror 6, tylko pakiety, których używamy wprost:

| Pakiet | Rola | Licencja |
|---|---|---|
| `codemirror` | `basicSetup`: numery linii, cofanie, zwijanie, wyszukiwanie, nawiasy | MIT |
| `@codemirror/lang-json` | składnia JSON; jego parser Lezer służy też do mapowania ścieżki JSON → pozycja w tekście i do linii błędu składni | MIT |
| `@codemirror/state`, `@codemirror/view` | rynna pewności, podświetlenie linii elementu (`StateField`, `gutter`, `Decoration.line`) | MIT |
| `@codemirror/language`, `@lezer/highlight` | kolory składni z tokenów `code-*` (DESIGN.md §2) | MIT |
| `@codemirror/lint` | falista linia i ikona przy błędzie składni lub schematu | MIT |

Zależności przechodnie: `@codemirror/*`, `@lezer/*`, `crelt`, `style-mod`, `w3c-keyname`, wszystkie MIT.

- **Walidacja schematem bez biblioteki.** Oficjalny schemat używa tylko `type`/`properties`/`items`, więc frontend ma ~25-liniowy walidator jak backend (`standards.py`), z tą samą poprawką literówki `repetingSectionGrid` (K-09) na kopii schematu.
- **Mapowanie ścieżki na linię** przez drzewo składni Lezer (to samo, którym edytor koloruje), więc działa też na niesformatowanym i właśnie edytowanym tekście, bez własnego parsera z pozycjami.
- Ekran ładuje się leniwie (`React.lazy`), więc CodeMirror i `jsonata` są poza głównym pakietem.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| `<textarea>` z numeracją linii | zero zależności, ale podświetlenie linii elementu, znaczniki w rynnie i falista linia błędu wymagałyby nakładek zsynchronizowanych z przewijaniem; „Formatuj” psuje natywne cofanie; wolna przy 3000 liniach |
| Monaco Editor | kilka razy cięższy, wymaga workerów; odrzucony już w ADR-0011 |
| `ajv` do schematu | pełny JSON Schema niepotrzebny: schemat używa trzech słów kluczowych; backend robi to samo bez biblioteki |
| Własny mini-parser JSON z pozycjami | ~60 linii i testy, a parser Lezer już jest w pakiecie edytora |

## Konsekwencje

- Chunk ekranu przeglądu: ok. 520 kB (170 kB gzip) z CodeMirror, `jsonata` i schematem; Vite ostrzega o rozmiarze ponad 500 kB. Ładuje się dopiero po otwarciu wyniku.
- Gdy schemat eUsługi zacznie używać innych słów kluczowych (`required`, `enum`), walidator trzeba rozszerzyć albo przejść na bibliotekę (nowy ADR), tak samo w backendzie.
- Testy komponentu działają w jsdom bez dodatkowych polyfilli; zmianę treści w testach robimy przez `EditorView.dispatch`.
