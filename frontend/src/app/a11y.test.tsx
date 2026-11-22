import { fireEvent, render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { expect, test } from "vitest";
import { FormPreview, type FormJson } from "../features/form-preview";
import wzorzec5 from "../features/form-preview/fixtures/wzorzec-5.json";
import wynik from "../features/review/fixtures/wynik-wzorzec-1.json";
import { setToken } from "../shared/api/token";
import { axeViolations } from "../test/axe";
import { fakeToken, server, sseStream } from "../test/server";
import { App } from "./App";
import { routes } from "./routes";

// Automated WCAG 2.1 AA checks of the main screens (FR-E4, ADR-0033); keyboard paths are in the screen tests.
const JOB_ID = "b6af199b-0000-4000-8000-000000000001";

function renderApp(path: string) {
  render(
    <App router={createMemoryRouter(routes, { initialEntries: [path] })} />,
  );
}

test("logowanie z błędem", async () => {
  renderApp("/logowanie");
  fireEvent.click(screen.getByRole("button", { name: "Zaloguj" }));
  await screen.findByRole("alert");
  expect(await axeViolations()).toEqual([]);
});

test("zadania: wgrywanie z kolejką plików i lista zadań", async () => {
  setToken(fakeToken());
  sessionStorage.setItem(
    "forms2json.jobs",
    JSON.stringify([
      {
        id: JOB_ID,
        fileName: "Wniosek.pdf",
        uploadedAt: new Date().toISOString(),
      },
    ]),
  );
  server.use(
    http.get(`*/api/v1/jobs/${JOB_ID}`, () =>
      HttpResponse.json({ status: "done", result: wynik }),
    ),
  );
  renderApp("/");
  await screen.findByText(/Maksymalnie 20 MB/);
  fireEvent.change(screen.getByLabelText("Wybierz pliki"), {
    target: { files: [new File(["x"], "notatka.txt")] },
  });
  await screen.findByText("Gotowe");
  expect(await axeViolations()).toEqual([]);
});

test("postęp zadania na żywo", async () => {
  setToken(fakeToken());
  const stream = sseStream();
  server.use(
    http.get(`*/api/v1/jobs/${JOB_ID}`, () =>
      HttpResponse.json({ status: "pending" }),
    ),
    http.get(`*/api/v1/jobs/${JOB_ID}/events`, () => stream.response()),
  );
  renderApp(`/zadania/${JOB_ID}`);
  await screen.findByText("Na żywo");
  stream.send({
    job_id: JOB_ID,
    step: "ingest",
    status: "started",
    message: "",
    ts: 1763700000,
  });
  await screen.findByText("Odczyt pliku: w toku.");
  expect(await axeViolations()).toEqual([]);
});

test("ekran przeglądu", async () => {
  setToken(fakeToken());
  server.use(
    http.get(`*/api/v1/jobs/${JOB_ID}`, () =>
      HttpResponse.json({ status: "done", result: wynik }),
    ),
  );
  renderApp(`/zadania/${JOB_ID}`);
  await screen.findByRole("heading", { level: 1, name: wynik.form.title });
  expect(await axeViolations()).toEqual([]);
});

test("podgląd formularza", async () => {
  render(
    <main>
      <title>Podgląd</title>
      <FormPreview form={wzorzec5 as FormJson} />
    </main>,
  );
  await screen.findAllByLabelText("Kod pocztowy");
  expect(await axeViolations()).toEqual([]);
});
