import { fireEvent, render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { expect, test } from "vitest";
import { fakeToken, server } from "../test/server";
import { setToken } from "../shared/api/token";
import { App } from "./App";
import { routes } from "./routes";

const JOB_ID = "b6af199b-0000-4000-8000-000000000001";

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

test("odrzuca token w złym formacie, przyjmuje poprawny", async () => {
  renderApp("/logowanie");
  const input = screen.getByLabelText("Token dostępu");

  fireEvent.change(input, { target: { value: "nie-token" } });
  fireEvent.click(screen.getByRole("button", { name: "Zaloguj" }));
  expect(screen.getByRole("alert").textContent).toContain(
    "To nie wygląda na token",
  );

  fireEvent.change(input, { target: { value: fakeToken(-60) } });
  fireEvent.click(screen.getByRole("button", { name: "Zaloguj" }));
  expect(screen.getByRole("alert").textContent).toContain("Token wygasł");

  fireEvent.change(input, { target: { value: `  ${fakeToken()}\n` } });
  fireEvent.click(screen.getByRole("button", { name: "Zaloguj" }));
  expect(await screen.findByRole("heading", { name: "Zadania" })).toBeDefined();
  expect(await screen.findByText(/Maksymalnie 20 MB na plik/)).toBeDefined();
  expect(screen.getByText("Nie masz jeszcze zadań")).toBeDefined();
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
  expect(screen.getByRole("alert").textContent).toContain(
    "Serwer nie przyjął tokenu",
  );
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

test("upload tworzy zadanie, status przechodzi z pending na done", async () => {
  setToken(fakeToken());
  let polls = 0;
  server.use(
    http.post("*/api/v1/jobs", () =>
      HttpResponse.json({ job_id: JOB_ID }, { status: 202 }),
    ),
    http.get(`*/api/v1/jobs/${JOB_ID}`, () =>
      HttpResponse.json(
        ++polls < 2
          ? { status: "pending" }
          : { status: "done", result: { title: "Wniosek" } },
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
  expect(await list.findByText("Gotowe", {}, { timeout: 4000 })).toBeDefined();
  fireEvent.click(
    list.getByRole("link", { name: "Zobacz wynik: Wniosek.pdf" }),
  );
  expect((await screen.findByLabelText("Wynik JSON")).textContent).toContain(
    '"title": "Wniosek"',
  );
});

test("błąd serwera przy uploadzie pokazuje detail", async () => {
  setToken(fakeToken());
  server.use(
    http.post("*/api/v1/jobs", () =>
      HttpResponse.json(
        { detail: "Zawartość pliku nie odpowiada rozszerzeniu .pdf." },
        { status: 415 },
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
