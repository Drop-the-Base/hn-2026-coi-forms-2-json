import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { sourceFiles } from "../../shared/sourceFiles";
import { server } from "../../test/server";
import { SourceView } from "./SourceView";

const JOB_ID = "b6af199b-0000-4000-8000-000000000002";
const SOURCE_TEXT = "## Strona 1\nWniosek o wydanie zaświadczenia";
const DOCX_TYPE =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:podglad");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  sourceFiles.clear();
});

function renderSource(sourceText: string | undefined = SOURCE_TEXT) {
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <SourceView jobId={JOB_ID} sourceText={sourceText} />
    </QueryClientProvider>,
  );
}

test("DOCX: plik z karty idzie do API, zwrócony PDF jest w iframe", async () => {
  // The body is not read: jsdom's File in FormData breaks undici's content-length.
  const preview = vi.fn(() =>
    HttpResponse.arrayBuffer(new TextEncoder().encode("%PDF").buffer, {
      headers: { "Content-Type": "application/pdf" },
    }),
  );
  server.use(http.post("*/api/v1/preview", preview));
  sourceFiles.set(
    JOB_ID,
    new File(["docx"], "wniosek.docx", { type: DOCX_TYPE }),
  );
  renderSource();

  expect(screen.getByRole("status").textContent).toBe(
    "Przygotowuję podgląd oryginału…",
  );
  const frame = await screen.findByTitle("Oryginał: wniosek.docx");
  expect(frame.getAttribute("src")).toBe("blob:podglad");
  expect(preview).toHaveBeenCalledOnce();
});

test("błąd konwersji: komunikat i tekst odczytany z dokumentu", async () => {
  server.use(
    http.post("*/api/v1/preview", () =>
      HttpResponse.json({ detail: "Nie udało się." }, { status: 422 }),
    ),
  );
  sourceFiles.set(JOB_ID, new File(["xlsx"], "wniosek.xlsx"));
  renderSource();

  expect(
    await screen.findByText(
      "Nie udało się przygotować podglądu oryginału. Poniżej tekst odczytany z dokumentu.",
    ),
  ).toBeDefined();
  expect(screen.getByText("Wniosek o wydanie zaświadczenia")).toBeDefined();
  expect(screen.queryByTitle("Oryginał: wniosek.xlsx")).toBeNull();
});

test("PDF z karty od razu w iframe, bez wywołania API", () => {
  const preview = vi.fn(() => HttpResponse.error());
  server.use(http.post("*/api/v1/preview", preview));
  sourceFiles.set(
    JOB_ID,
    new File(["%PDF"], "wniosek.pdf", { type: "application/pdf" }),
  );
  renderSource();
  expect(screen.getByTitle("Oryginał: wniosek.pdf")).toBeDefined();
  expect(preview).not.toHaveBeenCalled();
});

test("brak pliku po odświeżeniu: tekst bez wywołania API", () => {
  renderSource();
  expect(
    screen.getByText(
      "Pliku nie ma już w tej karcie (na przykład po odświeżeniu strony). Poniżej tekst odczytany z dokumentu.",
    ),
  ).toBeDefined();
});

test("brak pliku i tekstu: prośba o ponowne wgranie", () => {
  renderSource("");
  expect(
    screen.getByText(
      "Pliku nie ma już w tej karcie (na przykład po odświeżeniu strony).",
    ),
  ).toBeDefined();
  expect(screen.getByText(/Wgraj plik ponownie/)).toBeDefined();
});
