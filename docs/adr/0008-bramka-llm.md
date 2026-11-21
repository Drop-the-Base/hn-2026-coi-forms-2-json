# ADR-0008: Bramka LLM: Bifrost zamiast LiteLLM

- Status: Odrzucona (2026-11-21), przyjmujemy wariant bez bramki
- Data: 2026-11-21
- Wymagania: NFR-02, NFR-03, NFR-04, NFR-13, NFR-14, NFR-16

## Kontekst

Chcemy jednego punktu wejścia do modeli: routing między modelami, limity, zliczanie tokenów i kosztu, wyłącznik LLM (kill switch) i telemetrię OTel. Guardrails na razie nie są potrzebne. Bramka musi być lekka i w pełni open source, bez funkcji enterprise (NFR-04).

## Decyzja

**Bifrost** (Go, jeden kontener) jako `llm-gateway`, o ile weryfikacja potwierdzi:
- licencję Apache-2.0 w repozytorium;
- budżety, limity, wirtualne klucze, metryki Prometheus i eksport OTel w wersji OSS.

Kill switch: wyłączenie dostawcy w konfiguracji bramki albo flaga `LLM_ENABLED=false` w workerze. Przy wyłączonym LLM pipeline zwraca szkielet z blokami Standardów i niski confidence.

Jeśli weryfikacja wypadnie źle: brak bramki (YAGNI). Worker mówi bezpośrednio z runtime'em, a tokeny i koszt zbieramy z atrybutów OTel `gen_ai.usage.*`. Port `LlmClient` się nie zmienia.

## Rozstrzygnięcie (2026-11-21)

Bifrost ma licencję Apache-2.0, ale bramki nie wdrażamy. Guardrails piszemy sami w kodzie, więc bramka zostałaby tylko do routingu i liczenia tokenów. To samo daje adapter `LlmClient` z atrybutami OTel `gen_ai.usage.*`. Jeden kontener mniej (YAGNI). Obowiązuje plan „brak bramki" opisany wyżej, z wyłącznikiem `LLM_ENABLED=false`.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| **LiteLLM** (odrzucona) | 1) marzec 2026: przejęcie potoku publikacji na PyPI, wersje 1.82.7 i 1.82.8 z malware kradnącym poświadczenia (CVE-2026-33634, w katalogu CISA KEV); doniesienia o kolejnym incydencie z wersją 1.107.0 (październik 2026), niepotwierdzone niezależnie; 2) część funkcji w katalogu `enterprise/` na licencji komercyjnej (NFR-04); 3) śledzenie kosztów i kluczy wymaga Postgresa, czyli kolejnej usługi |
| Envoy AI Gateway, Kong | ciężkie, konfiguracja pod Kubernetes |
| Brak bramki | plan awaryjny opisany wyżej |

## Konsekwencje

- Kolejny kontener w compose, ale bez bazy danych.
- Guardrails są w Bifroście funkcją enterprise. Jeśli będą potrzebne, robimy je w kodzie (walidacja wyjścia pydantikiem już jest) albo osobnym ADR-em.
