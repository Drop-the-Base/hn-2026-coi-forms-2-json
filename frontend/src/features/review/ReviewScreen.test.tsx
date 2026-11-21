import { EditorView } from "@codemirror/view";
import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, expect, test, vi } from "vitest";
import ReviewPage from "./ReviewScreen";
import wynik from "./fixtures/wynik-wzorzec-1.json";

afterEach(() => vi.restoreAllMocks());

function renderReview(result: unknown = wynik) {
  const router = createMemoryRouter([
    {
      path: "*",
      element: (
        <ReviewPage
          result={result}
          jobId="b6af199b-0000-4000-8000-000000000001"
          fileName="wniosek.pdf"
        />
      ),
    },
  ]);
  render(<RouterProvider router={router} />);
}

function editor() {
  const dom = document.querySelector(".cm-editor") as HTMLElement;
  return EditorView.findFromDOM(dom) as EditorView;
}

function typeInEditor(change: { from: number; to?: number; insert: string }) {
  // The editor reports changes 300 ms after the last one; findBy* waits for that.
  editor().dispatch({ changes: change });
}

const pageTitle = () => screen.getByRole("heading", { level: 3 }).textContent;

test("pokazuje ocenę ogólną, liczniki i listę problemów", async () => {
  renderReview();
  expect(
    screen.getByRole("heading", {
      level: 1,
      name: "Wniosek o ustalenie numeru porządkowego nieruchomości",
    }),
  ).toBeDefined();
  expect(screen.getByText("1 błąd, 4 do sprawdzenia")).toBeDefined();
  expect(document.querySelectorAll(".issues .issue")).toHaveLength(5);
  expect(screen.getAllByText(/Średnia/).length).toBeGreaterThan(0);
  expect(screen.getByText("Zgodny ze schematem eUsługi")).toBeDefined();
  expect(pageTitle()).toBe("Dane");
});

test("kliknięcie problemu przenosi podgląd na stronę elementu i zaznacza go", async () => {
  renderReview();
  fireEvent.click(
    screen.getByRole("button", {
      name: /Pole adresu e-mail nie ma walidatora/,
    }),
  );
  expect(pageTitle()).toBe("Kontakt z urzędem");
  expect(screen.getByText("Problem 1 z 5")).toBeDefined();
  const current = document.querySelector(".eu-cell.is-current");
  expect(current?.textContent).toContain("Adres e-mail");

  fireEvent.keyDown(document, { key: "F8" });
  expect(pageTitle()).toBe("Dane");
  fireEvent.keyDown(document, { key: "F8" });
  expect(pageTitle()).toBe("Informacje o budynku");
  expect(screen.getByText("Problem 3 z 5")).toBeDefined();
  // Low-confidence element has a margin mark and a badge in the preview.
  expect(
    document.querySelector(".eu-cell.is-current .mark--low"),
  ).not.toBeNull();
});

test("błąd składni pokazuje linię i nie psuje podglądu", async () => {
  renderReview();
  typeInEditor({ from: 0, insert: "x" });
  expect(await screen.findByText(/Błąd składni w/)).toBeDefined();
  expect(screen.getByRole("button", { name: "linii 1" })).toBeDefined();
  expect(
    screen.getByText(/Podgląd sprzed ostatniej zmiany: JSON ma błąd składni/),
  ).toBeDefined();
  expect(pageTitle()).toBe("Dane");
  expect(
    (screen.getByRole("button", { name: "Pobierz JSON" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(screen.getByText("Popraw błąd składni, aby pobrać.")).toBeDefined();
});

test("błąd schematu blokuje pobranie z powodem", async () => {
  renderReview();
  const text = editor().state.doc.toString();
  const at = text.indexOf('"Wniosek o ustalenie');
  typeInEditor({ from: at, to: text.indexOf(",", at), insert: "42" });
  expect(await screen.findByText("1 niezgodność ze schematem")).toBeDefined();
  expect(screen.getByText(/„title” powinno mieć typ tekst/)).toBeDefined();
  expect(screen.getByText("Popraw 1 błąd schematu, aby pobrać.")).toBeDefined();
});

test("Pobierz JSON daje zmieniony JSON z nazwą z tytułu", async () => {
  let blob: Blob | undefined;
  URL.createObjectURL = vi.fn((b: Blob) => {
    blob = b;
    return "blob:wynik";
  });
  URL.revokeObjectURL = vi.fn();
  let fileName = "";
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    fileName = this.download;
  });
  renderReview();
  const text = editor().state.doc.toString();
  const at = text.indexOf("Wniosek o ustalenie");
  typeInEditor({ from: at, to: at + "Wniosek".length, insert: "Zgłoszenie" });
  await screen.findByRole("heading", {
    level: 1,
    name: /^Zgłoszenie o ustalenie/,
  });

  fireEvent.click(screen.getByRole("button", { name: "Pobierz JSON" }));
  expect(fileName).toBe(
    "zgloszenie-o-ustalenie-numeru-porzadkowego-nieruchomosci.json",
  );
  const downloaded = JSON.parse(await (blob as Blob).text());
  expect(downloaded.title).toBe(
    "Zgłoszenie o ustalenie numeru porządkowego nieruchomości",
  );
  expect(downloaded.confidence).toBeUndefined();
});

test("wynik w nieoczekiwanym formacie daje komunikat zamiast ekranu", () => {
  renderReview({ title: "Wniosek" });
  expect(screen.getByRole("alert").textContent).toContain(
    "nieoczekiwany format",
  );
});
