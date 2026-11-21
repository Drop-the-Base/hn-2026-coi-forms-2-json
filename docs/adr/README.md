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
| [0016](0016-router-react-router.md) | Routing we frontendzie: React Router | Zaakceptowana |
| [0017](0017-odczyt-arkuszy-openpyxl.md) | Odczyt arkuszy: openpyxl dla XLSX, biblioteka standardowa dla ODS | Proponowana |
| [0018](0018-klient-llm-openai-sdk.md) | Klient LLM: SDK `openai` z własną pętlą ponowień | Zaakceptowana |
| [0019](0019-uwierzytelnianie-jwt-pyjwt.md) | Uwierzytelnianie JWT: PyJWT, HMAC, token demo ze skryptu | Proponowana |
| [0020](0020-pydantic-w-domenie.md) | Pydantic w domenie: tylko dla modeli-kontraktów z LLM (`FormDraft`) | Zaakceptowana |
| [0021](0021-kolejka-aio-pika.md) | Kolejka zadań: `aio-pika` za portem `JobQueue` | Proponowana |
| [0022](0022-serwer-uvicorn-python-multipart.md) | Serwer ASGI `uvicorn` i `python-multipart` dla uploadu | Proponowana |
| [0023](0023-odczyt-pdf-pdfplumber.md) | Odczyt PDF: pdfplumber | Proponowana |
| [0024](0024-tracing-otel-pakiety.md) | Tracing OTel w `api` i `worker`: pakiety i propagacja przez RabbitMQ | Proponowana |
| [0025](0025-warunki-podgladu-jsonata.md) | Warunki `states` w podglądzie formularza: `jsonata` w przeglądarce | Proponowana |
| [0026](0026-frontend-typy-api-msw-css.md) | Frontend: typy z `openapi-typescript`, MSW w testach, CSS z design systemu zamiast Tailwind | Proponowana |
| [0027](0027-edytor-json-codemirror.md) | Edytor JSON na ekranie przeglądu: pakiety CodeMirror 6 | Proponowana |

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
