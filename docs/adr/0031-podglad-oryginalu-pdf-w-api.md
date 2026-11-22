# ADR-0031: Podgląd oryginału: DOC, DOCX, XLSX i ODS jako PDF z LibreOffice w API

- Status: Proponowana
- Data: 2026-11-21
- Wymagania: FR-E4, NFR-06, NFR-15

## Kontekst

Ekran przeglądu pokazuje obok wyniku oryginał wgranego pliku (zakładka „Oryginał"). Plik leży tylko w pamięci karty przeglądarki: serwer go usuwa po przetworzeniu (NFR-06). PDF i JPG/PNG przeglądarka pokazuje sama. DOC, DOCX, XLSX i ODS nie: dotąd widać było tylko tekst odczytany z dokumentu, bez układu, tabel i kratek. Właściciel chce wizualnego podglądu dla każdego przyjmowanego formatu.

LibreOffice headless jest już w obrazie workera do konwersji `.doc` ([ADR-0013](0013-polityka-licencji.md)), ale tylko moduł Writer. Obraz `api` nie ma LibreOffice.

## Decyzja

Bezstanowy endpoint **`POST /api/v1/preview`** (multipart `file`, JWT, te same reguły nazwy, rozszerzenia, treści i rozmiaru co `POST /jobs`) zwraca plik jako `application/pdf`. PDF, JPG i PNG odrzuca kodem 415 (nie potrzebują konwersji), błąd konwersji to 422 z komunikatem po polsku.

- Port `PdfRenderer` (`application/ports/pdf_renderer.py`), adapter `LibreOfficePdfRenderer` wołający `soffice --convert-to pdf` przez wspólny helper `adapters/outbound/libreoffice.py` (ten sam co `DocReader`): katalog tymczasowy na tmpfs, własny profil soffice, timeout `DOC_CONVERSION_TIMEOUT_SECONDS` z zabiciem całej grupy procesów.
- Konwersja działa w **API**, w wątku (`asyncio.to_thread`), nie blokuje pętli zdarzeń. Nic nie jest zapisywane poza katalogiem tymczasowym, który znika po odpowiedzi (NFR-06).
- Obraz `api` dostaje `libreoffice-writer-nogui` i `libreoffice-calc-nogui` (Calc dla XLSX i ODS). Licencja bez zmian: MPL-2.0, niezmodyfikowany program wywoływany jako proces.
- Frontend wysyła plik z pamięci karty tylko dla formatów spoza PDF/JPG/PNG i pokazuje wynik w tym samym `iframe` co PDF. Przy błędzie zostaje tekst z `source_text`.

## Rozważone alternatywy

| Opcja | Dlaczego nie |
|---|---|
| Konwersja w workerze przez RabbitMQ (RPC albo zadanie) | nowa kolejka, korelacja odpowiedzi i limit czasu po stronie API dla jednej konwersji pliku; dużo kodu na rzecz, którą API zrobi samo |
| Zapis PDF-a przez workera przy przetwarzaniu i serwowanie go z `GET /jobs/{id}` | plik i jego pochodne musiałyby żyć dłużej niż przetwarzanie (NFR-06), a wynik rośnie o megabajty |
| Renderowanie w przeglądarce (docx-preview, SheetJS) | nowe biblioteki per format, DOC i ODS bez wsparcia, inny wygląd niż oryginał |
| Osobny kontener z LibreOffice (np. Gotenberg) | nowa usługa w compose do utrzymania i zabezpieczenia, a LibreOffice i tak już mamy |

## Konsekwencje

- Obraz `api` rośnie o LibreOffice Writer i Calc (rząd kilkuset MB); rozmiar do zmierzenia po buildzie.
- Jedna konwersja to proces soffice (ok. 100–200 MB RAM, sekundy). Endpoint jest za JWT, ale równoległe podglądy nie mają limitu: przy problemach z pamięcią dodać semafor w `RenderPreview`.
- tmpfs `/tmp` w API rośnie do 160 MB (upload, kopia pliku, PDF, profil soffice), dochodzi tmpfs `/home/app`.
- Wygląd podglądu to wygląd z LibreOffice, nie z Worda czy Excela: drobne różnice w czcionkach i łamaniu stron są możliwe.
