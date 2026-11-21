# Architecture Decision Records (ADR)

Każda decyzja o frameworku, bibliotece, usłudze albo wzorcu architektonicznym ma tu swój plik. Dzięki temu wiemy **co** wybraliśmy, **dlaczego**, **co odrzuciliśmy** i **co jest wycofane**.

## Zasady

1. Nowa zależność albo zmiana decyzji = nowy ADR w tym samym PR-ze co kod.
2. ADR-ów nie przepisujemy. Zmiana decyzji to nowy ADR, a stary dostaje status `Zastąpiona przez ADR-XXXX`.
3. Nazwa pliku: `NNNN-krotki-opis.md`, numeracja rosnąca.
4. Każdy ADR wskazuje wymagania, których dotyczy (ID z [requirements.md](../requirements.md)).
5. Każda wybrana technologia ma sprawdzoną licencję zgodną z [ADR-0013](0013-polityka-licencji.md).

## Statusy

| Status | Znaczenie |
|---|---|
| Proponowana | do akceptacji przez Benka i Kubę albo do weryfikacji (np. licencja) |
| Zaakceptowana | obowiązuje |
| Odrzucona | rozważona i nie wybrana, zostaje dla historii |
| Wycofana (deprecated) | obowiązywała, nie stosujemy w nowym kodzie |
| Zastąpiona przez ADR-XXXX | zastąpiona nowszą decyzją |

## Rejestr

| ADR | Decyzja | Status |
|---|---|---|
| [0001](0001-rejestrowanie-decyzji.md) | Rejestrujemy decyzje w ADR | Zaakceptowana |
| [0002](0002-python-fastapi.md) | Backend: Python 3.14 + FastAPI | Zaakceptowana |
| [0003](0003-architektura-heksagonalna-abc.md) | Architektura heksagonalna, porty jako ABC | Zaakceptowana |
| [0004](0004-przetwarzanie-asynchroniczne-rabbitmq.md) | RabbitMQ + worker, tryb sync i async | Zaakceptowana |
| [0005](0005-pliki-tymczasowe-tmpfs.md) | Pliki tymczasowe na współdzielonym tmpfs | Zaakceptowana |
| [0006](0006-pipeline-czysty-python.md) | Pipeline w czystym Pythonie, bez frameworka orkiestracji | Zaakceptowana |
| [0007](0007-lokalny-runtime-llm.md) | Lokalny runtime LLM: Ollama, API zgodne z OpenAI | Proponowana |
| [0008](0008-bramka-llm.md) | Bramka LLM: Bifrost zamiast LiteLLM | Odrzucona: bez bramki |
| [0009](0009-obserwowalnosc-opentelemetry.md) | OTel Collector + Jaeger + Prometheus, bez Grafany | Zaakceptowana |
| [0010](0010-ewaluacje-pytest.md) | Ewaluacje: własny runner na pytest, DeepEval odłożony | Proponowana |
| [0011](0011-frontend-react-vite.md) | Frontend: React + Vite + TypeScript + TanStack Query | Zaakceptowana |
| [0012](0012-obraz-bazowy-slim.md) | Obraz workera: `python:3.14-slim` zamiast Alpine | Proponowana |
| [0013](0013-polityka-licencji.md) | Polityka licencji i lista zakazanych zależności | Zaakceptowana |
| [0014](0014-sse-postep-pipeline.md) | Postęp pipeline'u na żywo przez SSE | Proponowana |
| [0015](0015-narzedzia-backendu.md) | Narzędzia backendu: uv, ruff, mypy, pytest, pydantic-settings | Zaakceptowana |
| [0016](0016-router-react-router.md) | Routing we frontendzie: React Router | Proponowana |

## Szablon

```markdown
# ADR-NNNN: Tytuł

- Status: Proponowana
- Data: RRRR-MM-DD
- Wymagania: FR-xx, NFR-xx

## Kontekst
Jaki problem rozwiązujemy i jakie mamy ograniczenia.

## Decyzja
Co wybieramy, jednym-dwoma zdaniami, potem szczegóły.

## Rozważone alternatywy
| Opcja | Dlaczego nie |
|---|---|

## Konsekwencje
Co zyskujemy, co tracimy, co trzeba pilnować.
```
