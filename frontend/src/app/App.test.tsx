import { fireEvent, render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { expect, test } from "vitest";
import { fakeToken, server, sseStream, TEST_PASSWORD } from "../test/server";
import { setToken } from "../shared/api/token";
import { App } from "./App";
import wynik from "../features/review/fixtures/wynik-wzorzec-1.json";
import { routes } from "./routes";

const JOB_ID = "b6af199b-0000-4000-8000-000000000001";
const BATCH_ID = "ba7c0000-0000-4000-8000-000000000001";

function renderApp(path = "/") {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} />);
  return router;
}

function pickFiles(...files: File[]) {
  fireEvent.change(screen.getByLabelText("Wybierz pliki"), {
    target: { files },
  });
}

test("bez tokenu przekierowuje do logowania", () => {
  renderApp();
  expect(screen.getByRole("heading", { name: "Zaloguj się" })).toBeDefined();
});

test("odrzuca złe hasło, loguje poprawnym", async () => {
  renderApp("/logowanie");
  const input = screen.getByLabelText("Hasło");
  expect(input.getAttribute("type")).toBe("password");

  fireEvent.change(input, { target: { value: "zle-haslo" } });
  fireEvent.click(screen.getByRole("button", { name: "Zaloguj" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Nieprawidłowe hasło.",
  );
  expect(input.getAttribute("aria-describedby")).toBe("login-msg");
  expect(document.activeElement).toBe(input);

  fireEvent.change(input, { target: { value: TEST_PASSWORD } });
  fireEvent.click(screen.getByRole("button", { name: "Zaloguj" }));
  expect(await screen.findByRole("heading", { name: "Zadania" })).toBeDefined();
  expect(sessionStorage.getItem("forms2json.token")).not.toBeNull();
  expect(await screen.findByText(/Maksymalnie 20 MB na plik/)).toBeDefined();
  expect(screen.getByText("Nie masz jeszcze zadań")).toBeDefined();
});

test("logowanie bez połączenia pokazuje błąd sieci", async () => {
  server.use(http.post("*/api/v1/login", () => HttpResponse.error()));
  renderApp("/logowanie");
  fireEvent.change(screen.getByLabelText("Hasło"), {
    target: { value: TEST_PASSWORD },
  });
  fireEvent.click(screen.getByRole("button", { name: "Zaloguj" }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Brak połączenia z serwerem",
  );
});

test("token bez exp: brak czasu sesji w nagłówku", async () => {
  setToken(`eyJhbGciOiJIUzI1NiJ9.${btoa(JSON.stringify({ sub: "u" }))}.sig`);
  renderApp();
  expect(await screen.findByRole("button", { name: "Wyloguj" })).toBeDefined();
  expect(screen.queryByText(/Sesja do/)).toBeNull();
});

test("401 z API wraca do logowania z komunikatem", async () => {
  setToken(fakeToken());
  server.use(
    http.get("*/api/v1/config", () =>
      HttpResponse.json(
        { detail: "Invalid or expired token" },
        { status: 401 },
      ),
    ),
  );
  renderApp();
  await screen.findByRole("heading", { name: "Zaloguj się" });
  expect(screen.getByRole("alert").textContent).toContain("Sesja wygasła");
  expect(sessionStorage.getItem("forms2json.token")).toBeNull();
});

test("wyloguj czyści sesję", async () => {
  setToken(fakeToken());
  renderApp();
  fireEvent.click(await screen.findByRole("button", { name: "Wyloguj" }));
  expect(screen.getByRole("heading", { name: "Zaloguj się" })).toBeDefined();
  expect(sessionStorage.getItem("forms2json.token")).toBeNull();
});

test("walidacja pliku: wysyła tylko poprawne, pokazuje przyczyny", async () => {
  setToken(fakeToken());
  const big = new File(["x"], "skan.pdf");
  Object.defineProperty(big, "size", { value: 34.2 * 1024 * 1024 });
  renderApp();
  await screen.findByText(/Maksymalnie 20 MB/);

  pickFiles(
    new File(["%PDF-"], "Wniosek.PDF"),
    new File(["x"], "Zajęcie pasa: skan.pdf"),
    new File(["x"], "notatka.txt"),
    big,
  );

  expect(
    screen.getByText("Nazwa zawiera niedozwolony znak „:”."),
  ).toBeDefined();
  expect(screen.getByText(/Format TXT nie jest obsługiwany/)).toBeDefined();
  expect(screen.getByText(/Plik ma 34,2 MB, limit to 20 MB/)).toBeDefined();
  expect(screen.getByRole("button", { name: "Wyślij 1 plik" })).toBeDefined();
  expect(screen.getByText(/zostaną pominięte: 3/)).toBeDefined();
});

/** GET /jobs/{id} answers pending until `finish()`, then done (or failed). */
function mockJob(stream?: ReturnType<typeof sseStream>) {
  let final: object | null = null;
  server.use(
    http.get(`*/api/v1/jobs/${JOB_ID}`, () =>
      HttpResponse.json(final ?? { status: "pending" }),
    ),
    http.get(`*/api/v1/jobs/${JOB_ID}/events`, () =>
      stream ? stream.response() : HttpResponse.error(),
    ),
  );
  return (result: object = { status: "done", result: wynik }) =>
    void (final = result);
}

const event = (step: string, status: string, ts = 1763700000) => ({
  job_id: JOB_ID,
  step,
  status,
  message: "",
  ts,
});

test("upload tworzy zadanie, lista pokazuje krok z SSE, potem gotowe", async () => {
  setToken(fakeToken());
  const stream = sseStream();
  const finish = mockJob(stream);
  server.use(
    http.post("*/api/v1/jobs/batch", () =>
      HttpResponse.json(
        {
          batch_id: BATCH_ID,
          jobs: [{ file_name: "Wniosek.pdf", job_id: JOB_ID }],
        },
        { status: 202 },
      ),
    ),
  );
  renderApp();
  await screen.findByText(/Maksymalnie 20 MB/);

  pickFiles(new File(["%PDF-"], "Wniosek.pdf"));
  fireEvent.click(screen.getByRole("button", { name: "Wyślij 1 plik" }));

  const list = within(
    await screen.findByRole("table", { name: "Twoje zadania" }),
  );
  expect(list.getByRole("link", { name: "Wniosek.pdf" })).toBeDefined();
  expect(await list.findByText("W toku")).toBeDefined();
  stream.send(event("job", "progress"));
  stream.send(event("ingest", "started"));
  expect(await list.findByText("W toku: Odczyt pliku")).toBeDefined();
  finish();
  stream.send(event("job", "done"));
  stream.close();
  expect(await list.findByText("Gotowe")).toBeDefined();
  fireEvent.click(
    list.getByRole("link", { name: "Zobacz wynik: Wniosek.pdf" }),
  );
  expect(
    await screen.findByRole("heading", { level: 1, name: wynik.form.title }),
  ).toBeDefined();
  expect(screen.getByRole("button", { name: "Pobierz JSON" })).toBeDefined();
});

test("paczka: pliki idą po MAX_BATCH_FILES, lista oznacza paczkę, odrzucony zostaje", async () => {
  setToken(fakeToken());
  const BATCHES = [
    ["a.pdf", "b.pdf"],
    ["c.pdf", "d.pdf"],
  ];
  let requests = 0;
  server.use(
    http.get("*/api/v1/config", () =>
      HttpResponse.json({ max_upload_bytes: 1024, max_batch_files: 2 }),
    ),
    http.get("*/api/v1/jobs/:id/events", () => HttpResponse.error()),
    http.get("*/api/v1/jobs/:id", () =>
      HttpResponse.json({ status: "pending" }),
    ),
    // The body is not read: a jsdom File cannot be streamed in Node, so the answer goes by request number.
    http.post("*/api/v1/jobs/batch", () => {
      const n = ++requests;
      return HttpResponse.json(
        {
          batch_id: `ba7c000${n}-0000-4000-8000-000000000000`,
          jobs: BATCHES[n - 1].map((name, i) =>
            name === "d.pdf"
              ? { file_name: name, error: "Plik jest pusty." }
              : {
                  file_name: name,
                  job_id: `00000000-0000-4000-8000-00000000000${n}${i}`,
                },
          ),
        },
        { status: 202 },
      );
    }),
  );
  renderApp();
  await screen.findByText(/Maksymalnie 1 kB/);

  pickFiles(...BATCHES.flat().map((name) => new File(["%PDF-"], name)));
  fireEvent.click(screen.getByRole("button", { name: "Wyślij 4 pliki" }));

  expect(
    await screen.findByText("Serwer odrzucił plik: Plik jest pusty."),
  ).toBeDefined();
  expect(requests).toBe(2);
  const list = within(screen.getByRole("table", { name: "Twoje zadania" }));
  expect(list.getAllByText(/paczka ba7c0001/)).toHaveLength(2);
  expect(list.getByRole("link", { name: "c.pdf" })).toBeDefined();
  expect(list.queryByText(/paczka ba7c0002/)).toBeNull();
  expect(list.queryByRole("link", { name: "d.pdf" })).toBeNull();
});

test("nieznany typ błędu zadania pokazuje polski komunikat", async () => {
  setToken(fakeToken());
  server.use(
    http.get(`*/api/v1/jobs/${JOB_ID}`, () =>
      HttpResponse.json({ status: "failed", error: "NowyBladWorkera" }),
    ),
  );
  renderApp(`/zadania/${JOB_ID}`);
  expect(
    await screen.findByText(
      /Nie udało się przetworzyć pliku \(kod: NowyBladWorkera\)\. Wgraj plik ponownie\./,
    ),
  ).toBeDefined();
});

test("błąd serwera przy uploadzie pokazuje detail", async () => {
  setToken(fakeToken());
  server.use(
    http.post("*/api/v1/jobs/batch", () =>
      HttpResponse.json(
        {
          batch_id: BATCH_ID,
          jobs: [
            {
              file_name: "Wniosek.pdf",
              error: "Zawartość pliku nie odpowiada rozszerzeniu .pdf.",
            },
          ],
        },
        { status: 202 },
      ),
    ),
  );
  renderApp();
  await screen.findByText(/Maksymalnie 20 MB/);

  pickFiles(new File(["nie pdf"], "Wniosek.pdf"));
  fireEvent.click(screen.getByRole("button", { name: "Wyślij 1 plik" }));

  expect(
    await screen.findByText(
      "Serwer odrzucił plik: Zawartość pliku nie odpowiada rozszerzeniu .pdf.",
    ),
  ).toBeDefined();
  expect(screen.getByText("Nie masz jeszcze zadań")).toBeDefined();
});

test("postęp na żywo: kolejne zdarzenia aktualizują kroki, koniec pokazuje wynik", async () => {
  setToken(fakeToken());
  const stream = sseStream();
  const finish = mockJob(stream);
  renderApp(`/zadania/${JOB_ID}`);
  const steps = within(await screen.findByRole("list"));
  expect(await screen.findByText("Na żywo")).toBeDefined();

  stream.send(event("job", "progress"));
  stream.send(event("ingest", "started", 1763700000));
  stream.send(event("ingest", "done", 1763700018));
  stream.send(event("understand", "started", 1763700018));
  expect(
    await screen.findByText("Analiza treści przez model: w toku."),
  ).toBeDefined();
  expect(steps.getByText("Zakończono w 18 s.")).toBeDefined();
  expect(steps.getByText("(zakończony)")).toBeDefined();
  expect(steps.getAllByText("(oczekuje)")).toHaveLength(3);

  finish();
  stream.send(event("understand", "done", 1763700100));
  stream.send(event("job", "done"));
  stream.close();
  expect(
    await screen.findByRole("heading", { level: 1, name: wynik.form.title }),
  ).toBeDefined();
});

test("błąd przetwarzania: krok z błędem i komunikat z przyczyną", async () => {
  setToken(fakeToken());
  const stream = sseStream();
  const finish = mockJob(stream);
  renderApp(`/zadania/${JOB_ID}`);
  await screen.findByText("Na żywo");

  stream.send(event("ingest", "started"));
  stream.send(event("ingest", "failed", 1763700001));
  finish({ status: "failed", error: "ValueError" });
  stream.send(event("job", "failed"));
  stream.close();

  expect((await screen.findByRole("alert")).textContent).toContain(
    "Serwer przerwał pracę (ValueError).",
  );
  expect(screen.getByText("(błąd)")).toBeDefined();
  expect(screen.getByText("Przerwano po 1 s.")).toBeDefined();
  expect(screen.getByRole("link", { name: "Wgraj inny plik" })).toBeDefined();
});

test("zerwanie SSE: komunikat o utracie połączenia i polling do wyniku", async () => {
  setToken(fakeToken());
  const stream = sseStream();
  const finish = mockJob(stream);
  renderApp(`/zadania/${JOB_ID}`);
  await screen.findByText("Na żywo");

  stream.send(event("ingest", "started"));
  stream.close(); // no final event
  expect(await screen.findByText("Utracono połączenie na żywo")).toBeDefined();
  expect(screen.getByText("Odczyt pliku: w toku.")).toBeDefined();

  finish(); // the next poll (2 s) sees the result
  expect(
    await screen.findByRole(
      "heading",
      { level: 1, name: wynik.form.title },
      { timeout: 4000 },
    ),
  ).toBeDefined();
});

test("401 ze strumienia SSE wraca do logowania", async () => {
  setToken(fakeToken());
  let unauthorized = false;
  server.use(
    http.get(`*/api/v1/jobs/${JOB_ID}`, () =>
      unauthorized
        ? HttpResponse.json({ detail: "x" }, { status: 401 })
        : HttpResponse.json({ status: "pending" }),
    ),
    http.get(`*/api/v1/jobs/${JOB_ID}/events`, () => {
      unauthorized = true; // token expired between the two requests
      return HttpResponse.json({ detail: "x" }, { status: 401 });
    }),
  );
  renderApp(`/zadania/${JOB_ID}`);
  expect(
    await screen.findByRole("heading", { name: "Zaloguj się" }),
  ).toBeDefined();
});
