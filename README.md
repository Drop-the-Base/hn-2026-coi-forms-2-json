# forms2json: formularze COI do JSON

Zamienia papierowy formularz urzędowy (DOCX, PDF, XLSX, ODS) na JSON formularza eUsług. Pipeline łączy szablony ze Standardów z małym lokalnym modelem językowym (Ollama), liczy pewność (confidence) każdego elementu i listę problemów do przejrzenia. Urzędnik wgrywa plik w przeglądarce albo przez REST API, a dane nie opuszczają serwera: pliki leżą tylko w RAM (tmpfs) i znikają po zadaniu.

```mermaid
flowchart LR
    FE[frontend<br/>React, nginx :8080] -->|REST + JWT| API[api<br/>FastAPI]
    API -->|zadanie| MQ[(rabbitmq)]
    MQ --> W[worker<br/>pipeline]
    W -->|wynik| MQ
    API <-->|plik| TMP[(tmpfs /jobs)]
    W <-->|plik| TMP
    W -->|API OpenAI| LLM[Ollama<br/>na hoście]
    API -. OTLP .-> OC[otel-collector]
    W -. OTLP .-> OC
```

Szczegóły: [docs/architecture.md](docs/architecture.md).

## Wymagania wstępne

| Co | Wersja / uwagi |
| --- | --- |
| Docker z Compose v2 | sprawdzone na Docker 28.0, Compose 2.34 (macOS arm64) |
| [Ollama](https://ollama.com) na hoście | działa w tle na porcie 11434 **z oknem kontekstu 16384**: `OLLAMA_CONTEXT_LENGTH=16384 ollama serve` (w aplikacji: Settings → Context length). Przy domyślnych 4096 dłuższe formularze (np. 7) kończą się błędem `answer cut off` |
| Model | `ollama pull qwen2.5:7b-instruct` (ok. 4,7 GB, raz) |
| RAM | ok. 8 GB wolne dla modelu; GPU niewymagane (na CPU wolniej) |
| `openssl` | do wygenerowania sekretów |

Ollama w kontenerze zamiast na hoście: patrz [Profile](#profile-compose).

## Szybki start

```sh
cp .env.example .env
# uzupełnij sekrety w .env (APP_PASSWORD to hasło urzędnika do logowania; zapisz je):
sed -i.bak "s/^JWT_SECRET=$/JWT_SECRET=$(openssl rand -hex 32)/; s/^RABBITMQ_PASSWORD=$/RABBITMQ_PASSWORD=$(openssl rand -hex 16)/; s/^APP_PASSWORD=$/APP_PASSWORD=$(openssl rand -hex 12)/" .env && rm .env.bak
grep ^APP_PASSWORD= .env

# LLM: ustaw LLM_BASE_URL, LLM_MODEL i LLM_API_KEY (patrz "LLM w chmurze albo u organizatorów")

docker compose up -d --build
# z dashboardami (Jaeger, Prometheus, Perses):
# docker compose --profile observability up -d --build
docker compose ps          # api i rabbitmq: (healthy), reszta: Up
curl http://localhost:8080/health   # {"status":"ok"}

# token JWT dla curla: hasło z APP_PASSWORD wymienione na JWT (bez wygasania przy JWT_TTL_SECONDS=0)
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/login -H 'Content-Type: application/json' \
  -d "{\"password\":\"$(grep ^APP_PASSWORD= .env | cut -d= -f2-)\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
```

Potem:
- **przeglądarka**: http://localhost:8080, wpisz hasło z `APP_PASSWORD`, wgraj plik z `data/`;
- **terminal**: [REST API](#rest-api).

Koniec: `docker compose down` (pliki i wyniki w tmpfs znikają, obrazy zostają).

Jedno zadanie trwa kilka sekund z modelem w chmurze (Groq gpt-oss-120b) i 1–2 min z lokalną Ollamą na Apple M-series. Jeśli model nie zdąży, zadanie kończy się `LlmCallFailed`: podnieś `LLM_TIMEOUT_SECONDS` w `.env` i `docker compose up -d`.

## Konfiguracja

Zmienne w `.env` ([.env.example](.env.example)), czytane przez [backend/src/forms2json/config.py](backend/src/forms2json/config.py).

| Zmienna | `.env.example` | Domyślnie w kodzie | Opis |
| --- | --- | --- | --- |
| `JWT_SECRET` | – | **wymagana** | klucz HMAC JWT, min. 32 znaki |
| `JWT_ALGORITHM` | `HS256` | `HS256` | `HS256`, `HS384` albo `HS512` |
| `JWT_ISSUER` | `forms2json` | `forms2json` | `iss` tokenu |
| `JWT_AUDIENCE` | `forms2json-api` | `forms2json-api` | `aud` tokenu |
| `JWT_TTL_SECONDS` | `0` | `0` | ważność tokenu w sekundach; `0` = bez wygasania ([ADR-0032](docs/adr/0032-logowanie-haslem-jwt-bez-wygasania.md)) |
| `APP_PASSWORD` | – | **wymagana** | hasło urzędnika, które `POST /api/v1/login` wymienia na JWT; min. 8 znaków |
| `RABBITMQ_USER` | `forms2json` | – | użytkownik brokera (compose składa z niego `RABBITMQ_URL`) |
| `RABBITMQ_PASSWORD` | – | **wymagana** | hasło brokera |
| `MAX_UPLOAD_BYTES` | `20971520` | `20971520` | maks. rozmiar pliku (20 MB) |
| `MAX_BATCH_FILES` | `10` | `10` | maks. liczba plików w jednej paczce `POST /api/v1/jobs/batch` |
| `FILE_TTL_SECONDS` | `900` | `900` | po tym czasie sprzątacz usuwa plik, którego worker nie usunął |
| `RESULT_TTL_SECONDS` | `1800` | `1800` | jak długo API trzyma wynik w pamięci |
| `SYNC_TIMEOUT_SECONDS` | `120` | `120` | ile czeka `forms:convert`, zanim odda `202` |
| `LLM_BASE_URL` | `http://host.docker.internal:11434/v1` | `http://llm-runtime:11434/v1` | API zgodne z OpenAI (Ollama) |
| `LLM_MODEL` | `qwen2.5:7b-instruct` | `qwen3:1.7b` | model, musi być pobrany |
| `LLM_API_KEY` | `local` | `local` | klucz API dostawcy (nagłówek `Authorization`); Ollama go ignoruje; sekret, nie jest logowany |
| `LLM_RESPONSE_FORMAT` | `json_schema` | `json_schema` | `json_schema` (strict) albo `json_object` (schemat w prompcie) dla dostawców bez strict structured output |
| `LLM_TIMEOUT_SECONDS` | `120` | `120` | timeout jednego wywołania LLM |
| `LLM_MAX_INPUT_CHARS` | `30000` | `30000` | maks. długość tekstu dokumentu dla modelu |
| `LLM_MAX_OUTPUT_TOKENS` | `32768` | `32768` | maks. długość odpowiedzi modelu, u modeli rozumujących razem z tokenami myślenia; ucięta odpowiedź = błąd bez ponawiania (#103). Lokalna Ollama z oknem 16384: ustaw `4096` |
| `UNDERSTAND_FILL` | `true` | `true` | drugie wywołanie LLM dopełnia pola pominięte w pierwszej odpowiedzi (#173); `false` oszczędza około połowy tokenów |
| `CONFIDENCE_REVIEW_THRESHOLD` | `0.85` | `0.85` | element poniżej progu trafia do `to_review` |
| `OCR_LANG` | `pol` | `pol` | język Tesseracta dla obrazów i skanów PDF ([ADR-0029](docs/adr/0029-ocr-tesseract.md)) |
| `COST_PER_1M_INPUT_TOKENS` | `0` | `0` | stawka za 1M tokenów wejścia ([Koszt](#koszt)) |
| `COST_PER_1M_OUTPUT_TOKENS` | `0` | `0` | stawka za 1M tokenów wyjścia |
| `COST_PER_GPU_SECOND` | `0` | `0` | umowna stawka za sekundę pracy LLM (model lokalny) |
| `COST_CURRENCY` | `USD` | `USD` | waluta stawek, trafia do `usage.currency` |

### LLM w chmurze albo u organizatorów

Dowolny endpoint zgodny z OpenAI, tylko modele open source zgodne z [ADR-0013](docs/adr/0013-polityka-licencji.md) ([ADR-0028](docs/adr/0028-model-wymienny-open-source-w-chmurze.md)). Do chmury wysyłamy tylko pliki z publicznego `data/`. Przykład (OpenRouter, gpt-oss) w `.env`:

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-oss-120b
LLM_API_KEY=<klucz dostawcy>
LLM_RESPONSE_FORMAT=json_object   # gdy dostawca odrzuca strict json_schema
```

Potem `docker compose up -d`. Klucz trzymaj tylko w `.env` (poza repo).

Ustawiane przez `compose.yaml` (nie w `.env`): `RABBITMQ_URL`, `FILE_STORE_DIR=/jobs`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`, `OTEL_SEMCONV_STABILITY_OPT_IN`.

### Profile compose

| Profil | Usługi | Użycie |
| --- | --- | --- |
| domyślny | `frontend` (:8080), `api`, `worker`, `rabbitmq`, `otel-collector` | `docker compose up -d` |
| `observability` | `jaeger` (http://127.0.0.1:16686), `prometheus` (http://127.0.0.1:9090), `perses` (http://127.0.0.1:8081) | `docker compose --profile observability up -d` |
| `llm` | `llm-runtime` (Ollama w kontenerze) | w `.env`: `LLM_BASE_URL=http://llm-runtime:11434/v1`, potem `docker compose --profile llm up -d` i `docker compose exec llm-runtime ollama pull qwen2.5:7b-instruct` |

Na zewnątrz wystawiony jest tylko port 8080 (nginx: SPA + proxy `/api/` i `/health` do api). UI obserwowalności domyślnie tylko na 127.0.0.1; na serwerze `OBSERVABILITY_BIND=0.0.0.0` w `.env` wystawia je na zewnątrz (16686, 9090, 8081, bez logowania), a `COMPOSE_PROFILES=observability` sprawia, że `deploy.sh` je uruchamia.

### Wdrożenie na VPS

W `.env` ustaw `VPS_HOSTNAME`, `VPS_PASSWORD` i `VPS_PATH` (katalog z klonem repo na serwerze; opcjonalnie `VPS_USER`, domyślnie `root`), potem `./deploy.sh`. Skrypt loguje się przez SSH, w `VPS_PATH` robi `git pull --ff-only` i `docker compose up -d --build --remove-orphans`, potem `docker compose ps` i `curl localhost:8080/health`. Na serwerze musi być klon repo z własnym `.env` (konfiguracja aplikacji, LLM), Docker z Compose v2 i `curl`; lokalnie wystarczy OpenSSH ≥ 8.4 (hasło przez `SSH_ASKPASS`, bez `sshpass`). Wdrażany jest to, co jest wypchnięte na gałąź sprawdzoną na serwerze.

## REST API

Wszystko pod `/api/v1` poza `/login` wymaga nagłówka `Authorization: Bearer <JWT>`. Upload: `multipart/form-data`, pole `file`.

| Metoda i ścieżka | Opis | Odpowiedź |
| --- | --- | --- |
| `POST /api/v1/login` | bez JWT; JSON `{"password":"…"}` z hasłem `APP_PASSWORD` | `200 {"token":"<JWT>"}`; `401`, gdy hasło złe |
| `POST /api/v1/forms:convert` | tryb synchroniczny: czeka na wynik do `SYNC_TIMEOUT_SECONDS` | `200` JSON formularza eUsług; `202 {"job_id"}` + `Location`, gdy trwa dłużej; `422 {"detail","error"}`, gdy konwersja padła |
| `POST /api/v1/jobs` | tryb asynchroniczny: przyjmuje plik | `202 {"job_id"}` |
| `POST /api/v1/jobs/batch` | paczka (FR-E6): pole `files` powtórzone dla każdego pliku, najwyżej `MAX_BATCH_FILES`; każdy plik to osobne zadanie, odrzucony plik nie blokuje pozostałych | `202 {"batch_id","jobs":[{"file_name","job_id"} \| {"file_name","error"}]}`; `400`, gdy plików za dużo |
| `GET /api/v1/jobs/{id}` | stan zadania | `{"status":"pending"}`, `{"status":"done","result":{…}}`, `{"status":"failed","error":"<typ>"}` |
| `GET /api/v1/jobs/{id}/events` | postęp na żywo (SSE, `event: progress`, krok i status) | `text/event-stream` |
| `GET /api/v1/config` | limity dla frontendu | `{"max_upload_bytes":20971520,"max_batch_files":10}` |
| `GET /health` | bez JWT | `{"status":"ok"}` |

Błędy (`{"detail": "<komunikat po polsku>"}`):

| Kod | Kiedy |
| --- | --- |
| `400` | zła nazwa pliku (> 250 znaków albo znaki `;:><\/\|'*%$`); za dużo plików w paczce |
| `401` | brak, zły albo wygasły token |
| `404` | nieznane zadanie albo wynik wygasł (`RESULT_TTL_SECONDS`) |
| `413` | plik większy niż `MAX_UPLOAD_BYTES` |
| `415` | rozszerzenie spoza `.pdf .doc .docx .ods .xlsx .jpg .jpeg .png` albo zawartość niezgodna z rozszerzeniem |

### Przykłady

```sh
F="data/3. Wniosek o wydanie zaświadczenia - formularze do cyfryzacji/Wniosek o wydanie zaświadczenia.docx"

# synchronicznie: od razu JSON formularza (albo 202 z job_id po 120 s)
curl -H "Authorization: Bearer $TOKEN" -F "file=@$F" http://localhost:8080/api/v1/forms:convert

# asynchronicznie
curl -H "Authorization: Bearer $TOKEN" -F "file=@$F" http://localhost:8080/api/v1/jobs
# {"job_id":"7c0e…"}
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/jobs/<job_id>
curl -H "Authorization: Bearer $TOKEN" -F "files=@$F" -F "files=@inny.pdf" http://localhost:8080/api/v1/jobs/batch
curl -N -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/jobs/<job_id>/events
```

`result` zadania `done` (skrócony):

```json
{
  "form": {"title": "Wniosek o wydanie zaświadczenia", "tabs": [ … ], "flow": { … }},
  "confidence": {
    "overall": 0.994,
    "elements": {"tabs[1].questions[0].field": 0.97},
    "to_review": []
  },
  "issues": [
    {"code": "S-TITLE", "message": "…", "path": "title", "severity": "WARNING"}
  ],
  "usage": {"prompt_tokens": 1425, "completion_tokens": 521, "seconds": 61.2, "cost": 0.000526, "currency": "USD"},
  "source_text": "## Strona 1\nWniosek o wydanie zaświadczenia\n| Imię | Nazwisko |\n☐ odbiór osobiście…"
}
```

`form` to JSON formularza eUsług (to samo, co zwraca `forms:convert`). `severity`: `ERROR` albo `WARNING`. Ścieżki w `elements`, `to_review` i `path` wskazują element w `form`. `source_text` to tekst dokumentu w tej postaci, którą dostał model (strony `## Strona N`, tabele, pola wyboru `☐`/`☒`); serwer nie trzyma pliku po przetworzeniu (NFR-06), więc ekran przeglądu pokazuje ten tekst, gdy nie ma oryginału w pamięci karty.

### OpenAPI

nginx nie przekazuje `/docs` do api (http://localhost:8080/docs to strona SPA). Opcje:
- specyfikacja w repo: [frontend/openapi.json](frontend/openapi.json);
- świeża z działającego kontenera:
  `docker compose exec -T api python -c "import json; from forms2json.adapters.inbound.http.app import create_app; print(json.dumps(create_app().openapi()))" > openapi.json`;
- Swagger UI: http://localhost:8000/docs przy [backendzie uruchomionym lokalnie](#rozwój-lokalny).

## Frontend

http://localhost:8080 → ekran logowania → wklej token z `issue_token` → wgraj pliki (przeciągnij albo „Wybierz pliki”) → lista zadań ze statusem → „Zobacz wynik”. Token żyje w karcie przeglądarki (`sessionStorage`); po wygaśnięciu UI wraca do logowania.

## Deklaracja dostępności

Panel urzędnika ma spełniać **WCAG 2.1 na poziomie AA** (ustawa o dostępności cyfrowej podmiotów publicznych).

Jak sprawdzamy:
- **lint**: `eslint-plugin-jsx-a11y` (reguły `recommended`) w `npm run lint`;
- **axe**: `axe-core` w Vitest (`frontend/src/app/a11y.test.tsx`) na ekranach logowania, wgrywania z listą zadań, postępu, przeglądu i podglądu formularza, bez błędów WCAG 2.1 A/AA ([ADR-0033](docs/adr/0033-narzedzia-dostepnosci-frontendu.md));
- **kontrast**: `python3 frontend/design/kontrast.py` liczy kontrast par tokenów (tekst 4,5:1, elementy UI 3:1);
- **klawiatura**: testy ekranów przechodzą główne ścieżki rolami i etykietami; link „Przejdź do treści”, widoczny fokus, postęp zadania ogłaszany przez `aria-live="polite"`.

Znane ograniczenia:
- kliknięcie pola w podglądzie wybiera je do edycji tylko myszą; z klawiatury ten sam wybór jest w liście „Struktura”;
- oryginał dokumentu (PDF w ramce, obraz skanu) jest dostępny tak, jak sam plik; skan nie ma warstwy tekstowej;
- testy axe w jsdom nie liczą kontrastu na żywo ani układu; brak jeszcze audytu z czytnikiem ekranu (NVDA, VoiceOver) i testu e2e klawiaturą w CI.

Problemy z dostępnością zgłaszaj jako issue z etykietą `frontend`.

## Obserwowalność

`docker compose --profile observability up -d`, potem:
- Jaeger http://127.0.0.1:16686: trace zadania ze spanem na każdy krok pipeline'u; zakładka Monitor: liczba wywołań, błędy i latencja per usługa i operacja;
- Prometheus http://127.0.0.1:9090: metryki z otel-collectora;
- Perses http://127.0.0.1:8081/projects/forms2json/dashboards/koszty: dashboard kosztu i jakości (koszt łączny, na zadanie i na wywołanie LLM, tokeny we/wy, zadania wg wyniku, błędy LLM, czasy p50/p95, confidence, RAM i CPU per kontener). Dashboard jest kodem w `deploy/perses/resources/` (ADR-0030); UI jest tylko do odczytu, zmiany rób w pliku i zrestartuj `perses`.

Bez tego profilu otel-collector loguje błąd eksportu do jaegera; nie wpływa to na działanie.

### Logi

`docker compose logs -f api worker`. Format: `czas poziom serwis [job_id] [trace_id] komunikat`, poziom z `LOG_LEVEL` (domyślnie `INFO`):

```
2026-11-21 10:00:01,234 INFO worker [3f2c…] [4bf92f3577b34da6a3ce929d0e0e4736] LLM qwen3:8b attempt 1/3: tokens in 5120 out 812, 41.3s, finish_reason stop
```

Zdarzenia: api: przyjęto/odrzucono plik, wynik dotarł; worker: zadanie odebrane, start/koniec kroku z czasem, każde wywołanie LLM (429 i timeout jako `WARNING`), koniec zadania (confidence, liczba ERROR/WARNING, tokeny). Treść dokumentu, odpowiedź modelu, nazwa pliku, klucz API i JWT nie trafiają do logów; błąd to tylko typ wyjątku.

Z logu do trace'a: skopiuj `trace_id` i wklej w pole wyszukiwania Jaegera (http://127.0.0.1:16686/trace/<trace_id>). `-` znaczy brak spanu (np. start usługi albo brak `OTEL_EXPORTER_OTLP_ENDPOINT`).

### Metryki

Eksport co 60 s (NFR-13, NFR-14), zasoby kontenerów co 15 s (`docker_stats` w otel-collectorze, ADR-0030). Nazwy w Prometheusie:

| Metryka | Co mierzy | Etykiety |
| --- | --- | --- |
| `forms2json_job_duration_seconds` | czas zadania; `_count` to liczba zadań | `outcome` (`done`/`failed`), `error_type` |
| `forms2json_pipeline_step_duration_seconds` | czas kroku pipeline'u | `step`, `error_type` |
| `gen_ai_client_token_usage` | tokeny na wywołanie LLM | `gen_ai_token_type` (`input`/`output`), `gen_ai_request_model` |
| `forms2json_job_cost` | koszt zadania, to samo co `usage.cost` w wyniku ([Koszt](#koszt)) | `gen_ai_request_model` |
| `forms2json_llm_call_cost` | koszt tokenów jednego wywołania LLM | `gen_ai_token_type` (`input`/`output`), `gen_ai_request_model` |
| `forms2json_llm_errors_total` | nieudane próby wywołania LLM | `error_type` (`429`, `413`, `APITimeoutError`, ...), `gen_ai_request_model` |
| `forms2json_job_confidence` | confidence ogólny zadania | |
| `http_server_request_duration_seconds` | żądania HTTP do `api` | `http_route`, `http_response_status_code` |
| `container_memory_usage_total_bytes` | RAM kontenera (jak `docker stats`) | `compose_service`, `container_name` |
| `container_cpu_utilization_ratio` | CPU kontenera w procentach (100 = jeden rdzeń), mimo sufiksu `_ratio` | `compose_service`, `container_name` |
| `traces_span_metrics_*` | metryki z trace'ów liczone przez Jaegera dla zakładki Monitor | `service_name`, `span_name` |

Przykłady: `sum by (outcome) (forms2json_job_duration_seconds_count)`, `histogram_quantile(0.95, sum by (le, step) (rate(forms2json_pipeline_step_duration_seconds_bucket[5m])))`, `forms2json_job_cost_sum / forms2json_job_cost_count`.

### Koszt

`usage.cost` w wyniku zadania = tokeny wejścia × `COST_PER_1M_INPUT_TOKENS` / 1M + tokeny wyjścia × `COST_PER_1M_OUTPUT_TOKENS` / 1M + czas LLM × `COST_PER_GPU_SECOND`, w walucie `usage.currency` (`COST_CURRENCY`). Ponowienia też kosztują, więc są wliczone. Stawki ustaw w `.env` z cennika dostawcy (np. Groq gpt-oss-120b ok. 0.15 / 0.60 USD za 1M, do potwierdzenia), domyślnie 0. Dashboard: Perses (wyżej).

### Droga do produkcji

Obserwowalność wystarcza na demo i pilotaż. Przed produkcją brakuje:

| Brak | Skutek | Rozwiązanie |
| --- | --- | --- |
| Dashboard liczy sumy od startu workera | restart workera zeruje panele | `rate()`/`increase()` w panelach ([#145](../../issues/145)) |
| Prometheus i Jaeger bez trwałego zapisu | restart kontenera kasuje historię metryk i trace'ów | wolumeny z retencją; Jaeger na trwałym storage (np. OpenSearch, Apache-2.0) |
| Logi tylko w `docker logs` | brak wyszukiwania po logach wielu replik | logi przez OTLP do otel-collectora i dalej do magazynu logów zgodnego z ADR-0013 (np. OpenSearch, VictoriaLogs); Loki odpada, AGPL |
| Brak alertów | nikt nie wie, że LLM zwraca 429 albo zadania padają | Alertmanager (Apache-2.0) z regułami na `forms2json_llm_errors_total` i `outcome="failed"` |
| otel-collector czyta `docker.sock` (grupa root, ADR-0030) | przejęty Collector steruje Dockerem na hoście | w k8s `kubeletstats` zamiast socketu |
| Perses bez logowania | dostęp tylko z localhosta | reverse proxy z SSO albo natywne uwierzytelnianie Perses |

## Rozwój lokalny

Wymaga [uv](https://docs.astral.sh/uv/) i Node.js 24.

```sh
# 1. RabbitMQ
docker run -d --rm --name rabbit --user rabbitmq \
  --tmpfs /var/lib/rabbitmq:uid=100,gid=101,mode=0700 -p 5672:5672 rabbitmq:4.1.4-alpine

# 2. API (terminal 1), Swagger: http://localhost:8000/docs
cd backend
export JWT_SECRET=local-dev-secret-local-dev-secret-123   # min. 32 znaki
export APP_PASSWORD=haslo-dev-123                         # hasło do logowania, min. 8 znaków
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
export FILE_STORE_DIR=$(mktemp -d)
uv run uvicorn forms2json.bootstrap:create_api --factory --port 8000

# 3. worker (terminal 2, te same trzy zmienne)
LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=qwen2.5:7b-instruct \
  uv run python -m forms2json.adapters.inbound.worker

# 4. logowanie w przeglądarce hasłem z APP_PASSWORD; token dla skryptów bez hasła (ten sam JWT_SECRET):
uv run python -m forms2json.adapters.inbound.http.issue_token demo

# 5. frontend (terminal 3): http://localhost:5173, /api idzie przez proxy Vite na :8000
cd frontend && npm ci && npm run dev
```

## Testy i ewaluacje

| Co | Komenda (katalog) |
| --- | --- |
| backend: lint, format, typy, testy | `uv run ruff check && uv run ruff format --check && uv run mypy src tests && uv run pytest` (`backend/`) |
| backend: integracyjne (RabbitMQ, Ollama) | `uv run pytest -m integration` (`backend/`, z działającymi usługami jak w [Rozwoju lokalnym](#rozwój-lokalny)) |
| ewaluacje jakości (ADR-0010) | `EVAL_PREDICTED_DIR=<wyniki> EVAL_GOLDEN_DIR=tests/evals/dataset/golden uv run pytest -m evals` (`backend/`); pliki parowane po nazwie (`3.json` …) |
| jakość czytnika DOCX bez LLM: pokrycie tekstu z PDF, kratki, listy, przypisy | `uv run python -m tests.evals.reader_eval --name <nazwa> [--baseline <nazwa>]` (`backend/`) |
| frontend | `npm run lint && npx prettier --check . && npx vitest run && npm run build` (`frontend/`) |

### Ewaluacja przez działającą aplikację

Skrypt wysyła formularze 1–9 (plik DOCX, potem PDF, potem ODS/XLSX z `data/N. …`) do API, czeka na wynik i liczy metryki względem wzorców (1 i 5: JSON-y COI z `data/`, reszta: `tests/evals/dataset/golden/`). W `backend/`, z działającym `docker compose`:

```bash
uv run python -m tests.evals.run_eval --forms 1,3 --name groq-1 --token-file <plik z JWT>
uv run python -m tests.evals.run_eval --forms 1,3 --name groq-2 --token-file <plik z JWT> --baseline groq-1
```

- adres API: `--api-url` albo `EVAL_API_URL` (domyślnie http://localhost:8080); token: `--token-file` albo `EVAL_TOKEN`
- `--forms` domyślnie 1–9, sekwencyjnie z `--delay` sekund przerwy (limity dostawcy LLM), `--timeout` na zadanie
- przebieg trafia do `backend/tests/evals/runs/<nazwa>/` (`N.json` wynik zadania, `scores.json` metryki), katalog jest w `.gitignore`
- tabela Markdown: per formularz i średnia; `--baseline <nazwa>` dopisuje deltę w nawiasie. Zadanie `failed` liczy się jako pusty formularz (recall 0), w kolumnie status widać typ błędu (np. `LlmRequestTooLarge`)

Złote JSON-y formularzy 2, 3, 4, 6, 7, 8, 9 i decyzje przy ich tworzeniu: [backend/tests/evals/dataset/](backend/tests/evals/dataset/README.md). CI (GitHub Actions) uruchamia testy backendu i frontendu.

## Struktura repo

| Ścieżka | Zawartość |
| --- | --- |
| `backend/src/forms2json/domain` | model formularza, reguły, bloki ze Standardów |
| `backend/src/forms2json/application` | pipeline (ingest → understand → compose → validate), porty, use case'y |
| `backend/src/forms2json/adapters` | HTTP (FastAPI), worker, czytniki plików, LLM, RabbitMQ, tmpfs |
| `backend/tests` | `unit`, `integration`, `evals` |
| `frontend/` | SPA React + Vite, `design/` z prototypami ekranów |
| `deploy/` | konfiguracja otel-collectora, Jaegera, Prometheusa i Perses (dashboard jako kod) |
| `data/` | materiały konkursowe (formularze 1–9) |
| `docs/` | wymagania, architektura, ADR |

## Znane ograniczenia

| Co | Stan |
| --- | --- |
| Formularz 7 (ODS) | model nie zawsze zwraca poprawny JSON, zadanie może skończyć się błędem ([#103](../../issues/103)); złoty JSON jest w `backend/tests/evals/dataset/golden/7.json` |
| OCR (JPG, PNG, skany PDF) | Tesseract `pol`; kratki w skanie wychodzą jako śmieci, confidence elementów ograniczony średnią pewnością OCR dokumentu |
| Jedna replika API | wyniki zadań w pamięci procesu api, giną przy restarcie |

Niespójności danych wejściowych ([docs/analiza-i-charakterystyka-danych.md](docs/analiza-i-charakterystyka-danych.md)):
- **Formularz 7 (K-12)**: tytuł mówi o psach ras uznawanych za agresywne, treść o chartach i ich mieszańcach (prawo łowieckie). Pola bierzemy z treści, tytuł przepisujemy bez zmian.
- **Formularz 9 (K-13)**: trzy wnioski w jednym dokumencie. Wynik to jeden JSON z RADIO „Rodzaj wniosku” i sekcjami `SHOW`.
- Pozostałe decyzje (K-01..K-14): [docs/requirements.md](docs/requirements.md).

## Licencje

Tylko open source bez copyleftu (bez AGPL/GPL, SSPL, BSL, modeli z ograniczeniami użycia): [ADR-0013](docs/adr/0013-polityka-licencji.md). Każda biblioteka ma swój ADR: [rejestr](docs/adr/README.md).

## Dokumentacja

| Plik | Po co |
| --- | --- |
| [docs/requirements.md](docs/requirements.md) | wymagania FR/NFR, decyzje K-xx |
| [docs/architecture.md](docs/architecture.md) | usługi, przepływ, pipeline |
| [docs/coding-rules.md](docs/coding-rules.md) | zasady kodu |
| [docs/adr/README.md](docs/adr/README.md) | decyzje architektoniczne |
| [docs/analiza-i-charakterystyka-danych.md](docs/analiza-i-charakterystyka-danych.md) | dane wejściowe i niespójności |
| [docs/propozycja-slownika.md](docs/propozycja-slownika.md) | propozycja nowego słownika |
| [frontend/DESIGN.md](frontend/DESIGN.md) | system wizualny frontendu |
