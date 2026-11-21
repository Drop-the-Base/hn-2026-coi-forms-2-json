# ADR-0013: Polityka licencji i lista zakazanych zależności

- Status: Zaakceptowana
- Data: 2026-11-21
- Wymagania: NFR-02, NFR-03, NFR-04

## Kontekst

Zadanie dopuszcza tylko rozwiązania open source bez copyleftu (wymienia AGPL i GNU GPL), bez licencji komercyjnych i bez zewnętrznych API. Wiele popularnych narzędzi AI ma licencje źródłowe (nie open source) albo model open-core.

## Decyzja

**Dozwolone**: MIT, BSD-2/3, Apache-2.0, ISC, PSF, Zlib, Unlicense.

**Dozwolone warunkowo** (tylko jako niezmodyfikowana usługa albo narzędzie, nie kod w naszym repo): MPL-2.0 (RabbitMQ, LibreOffice), LGPL przy dynamicznym linkowaniu. Każdy taki przypadek odnotowujemy w tabeli niżej.

**Zakazane**: AGPL, GPL, SSPL, BSL/BUSL, Elastic License 2.0, Commons Clause, licencje modeli z ograniczeniami użycia (Llama, Gemma), funkcje enterprise narzędzi open-core.

Przed dodaniem zależności sprawdzamy licencję na PyPI/npm **i** w repozytorium (plik `LICENSE`).

### Zakazane konkretne zależności

| Zależność | Licencja | Zamiennik |
|---|---|---|
| PyMuPDF (`fitz`) | AGPL-3.0 | `pypdf`, `pdfplumber`, `pypdfium2` |
| Grafana, Tempo, Loki | AGPL-3.0 | Jaeger SPM, Perses (patrz [ADR-0009](0009-obserwowalnosc-opentelemetry.md)) |
| Redis 8+ | AGPL / SSPL / RSAL | Valkey (BSD) |
| Arize Phoenix | Elastic License 2.0 | Jaeger + OTel |
| antiword, catdoc | GPL | LibreOffice headless |
| Modele Llama, Gemma, część Qwen2.5 | licencje własne | Bielik, Qwen3 (Apache-2.0) |
| LiteLLM | MIT + katalog enterprise; incydenty bezpieczeństwa | patrz [ADR-0008](0008-bramka-llm.md) |

### Wyjątki warunkowe

| Zależność | Licencja | Uzasadnienie |
|---|---|---|
| RabbitMQ | MPL-2.0 | niezmodyfikowany oficjalny obraz |
| LibreOffice (konwersja `.doc`) | MPL-2.0 | niezmodyfikowany program wywoływany jako proces |

## Konsekwencje

- Agent, który chce dodać zależność, najpierw sprawdza tę listę i licencję.
- Bezpieczeństwo łańcucha dostaw: wersje przypięte w lockfile, obrazy przypięte co do digestu, aktualizacje świadomie w osobnych PR-ach.
