# ADR-0010: Ewaluacje: własny runner na pytest, DeepEval odłożony

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-T4, NFR-11, NFR-03

## Kontekst

Musimy wiedzieć, czy zmiana promptu, modelu albo kroku pipeline'u poprawia wynik. Dane: 2 wzorcowe JSON-y i 7 formularzy bez wzorca. Wynik to JSON o znanej strukturze, więc większość jakości da się zmierzyć **deterministycznie**, bez LLM-a w roli sędziego.

## Decyzja

1. **Zbiór danych** w `evals/dataset/`: każdy przypadek to plik źródłowy + złoty JSON. Złote JSON-y dla formularzy 2, 3, 4, 6, 7, 8, 9 przygotowujemy ręcznie według Standardów (osobne issues). Jeden formularz w kilku formatach = kilka przypadków z tym samym złotym JSON-em, co mierzy odporność na format.
2. **Metryki deterministyczne** (własny kod, `tests/evals/`):
   - zgodność z regułami R/S (liczba naruszeń);
   - recall i precision sekcji i pól (dopasowanie po znormalizowanej etykiecie);
   - trafność typów pól;
   - trafność warunków `SHOW` (pole sterujące + wartość);
   - kalibracja: czy niski confidence pokrywa się z faktycznymi błędami.
3. **Runner**: `pytest -m evals`, wynik jako tabela Markdown do opisu PR-a. Nie blokuje merge'a.

## Rozważone alternatywy

| Opcja | Dlaczego nie (na teraz) |
|---|---|
| DeepEval | metryki to głównie LLM-as-judge, domyślnie z OpenAI; przy lokalnym sędzi wolne i niestabilne; domyślnie wysyła telemetrię (trzeba `DEEPEVAL_TELEMETRY_OPT_OUT`); nasze metryki są strukturalne. Wracamy do niego, jeśli będziemy oceniać jakość tekstów (opisy, prosty język) |
| promptfoo | narzędzie Node, dodatkowy runtime w repo backendu |
| Inspect AI | dobre do agentów, za dużo jak na porównanie JSON-ów |

## Konsekwencje

- Złote JSON-y to praca ręczna (około godziny na prosty formularz, kilka na nr 8 i 9). To też nasza najlepsza dokumentacja „jak powinien wyglądać wynik".
- Poprawki z panelu frontendu (FR-T2) można dodać do zbioru jako nowe złote JSON-y przez PR.
