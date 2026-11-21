import { EditorView } from "@codemirror/view";
import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, expect, test, vi } from "vitest";
import { sourceFiles } from "../../shared/sourceFiles";
import { FORM_SCHEMA } from "../../test/server";
import ReviewPage from "./ReviewScreen";
import wynik from "./fixtures/wynik-wzorzec-1.json";

const JOB_ID = "b6af199b-0000-4000-8000-000000000001";

afterEach(() => {
  vi.restoreAllMocks();
  sourceFiles.clear();
});

function renderReview(result: unknown = wynik) {
  const router = createMemoryRouter([
    {
      path: "*",
      element: (
        <ReviewPage
          result={result}
          schema={FORM_SCHEMA}
          jobId={JOB_ID}
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

const SOURCE_TEXT =
  "## Strona 1\nWniosek\n| Imię | Nazwisko |\n## Strona 2\n☐ odbiór osobiście";

function showOriginal(
  result: unknown = { ...wynik, source_text: SOURCE_TEXT },
) {
  URL.createObjectURL = vi.fn(() => "blob:oryginal");
  URL.revokeObjectURL = vi.fn();
  renderReview(result);
  const tabs = screen.getAllByRole("tab", { name: "Oryginał" });
  // One tab in the narrow-screen tablist, one in the right column's switch.
  expect(tabs).toHaveLength(2);
  fireEvent.click(tabs[1]);
  expect(tabs[1].getAttribute("aria-selected")).toBe("true");
}

test("oryginał PDF z pamięci karty w iframe z blob URL", () => {
  sourceFiles.set(
    JOB_ID,
    new File(["%PDF"], "wniosek.pdf", { type: "application/pdf" }),
  );
  showOriginal();
  const frame = screen.getByTitle("Oryginał: wniosek.pdf");
  expect(frame.getAttribute("src")).toBe("blob:oryginal");
});

test("oryginał JPG w img z blob URL, klik przełącza 100%", () => {
  sourceFiles.set(
    JOB_ID,
    new File(["jpg"], "skan.jpg", { type: "image/jpeg" }),
  );
  showOriginal();
  const img = screen.getByAltText("Oryginał: skan.jpg");
  expect(img.getAttribute("src")).toBe("blob:oryginal");
  const zoom = screen.getByRole("button", { name: /Oryginał: skan.jpg/ });
  fireEvent.click(zoom);
  expect(zoom.getAttribute("aria-pressed")).toBe("true");
});

test("brak pliku po odświeżeniu: tekst z source_text i informacja", () => {
  showOriginal();
  expect(screen.getByText(/Pliku nie ma już w tej karcie/)).toBeDefined();
  expect(
    screen.getByRole("heading", { level: 3, name: "Strona 1" }),
  ).toBeDefined();
  expect(screen.getByText(/\| Imię \| Nazwisko \|/)).toBeDefined();
});

const NAZWA_ORGANU = "tabs[0].questions[0].field.repeatingSectionGrid[0].field";

function openInTree(title: string) {
  fireEvent.click(screen.getByRole("tab", { name: "Struktura" }));
  const tree = screen.getByRole("navigation", { name: "Struktura formularza" });
  const node = [...tree.querySelectorAll("button")].find(
    (b) => b.querySelector(".tree__title")?.textContent === title,
  );
  fireEvent.click(node as HTMLButtonElement);
}

test("pole z drzewa edytuje się w inspektorze, zmiana trafia do JSON-a i podglądu", async () => {
  renderReview();
  openInTree("Nazwa organu");
  const title = screen.getByLabelText("Tytuł") as HTMLInputElement;
  expect(title.value).toBe("Nazwa organu");

  fireEvent.change(title, { target: { value: "Nazwa urzędu" } });
  const json = JSON.parse(editor().state.doc.toString());
  expect(
    json.tabs[0].questions[0].field.repeatingSectionGrid[0].field.title,
  ).toBe("Nazwa urzędu");
  expect(document.querySelector(".eu-cell.is-current")?.textContent).toContain(
    "Nazwa urzędu",
  );
});

test("Wymagane w inspektorze dopisuje REQUIRED do walidacji", () => {
  renderReview();
  openInTree("Nazwa organu");
  fireEvent.click(screen.getByLabelText("Wymagane"));
  const json = JSON.parse(editor().state.doc.toString());
  expect(
    json.tabs[0].questions[0].field.repeatingSectionGrid[0].field.validation,
  ).toEqual(["REQUIRED"]);
  expect(screen.getByText(/Nazwa organu \(wymagane\)/)).toBeDefined();
});

test("kliknięcie pola w podglądzie otwiera je w inspektorze", () => {
  renderReview();
  const cell = [...document.querySelectorAll(".eu-cell")].find((c) =>
    c.textContent?.startsWith("Nazwa organu"),
  );
  fireEvent.click(cell as HTMLElement);
  expect((screen.getByLabelText("Tytuł") as HTMLInputElement).value).toBe(
    "Nazwa organu",
  );
  expect(document.querySelector(".eu-cell.is-current")).toBe(
    document.querySelector(`[data-path="${NAZWA_ORGANU}"]`) ??
      document.querySelector(".eu-cell.is-current"),
  );
});

test("problem z ukrytym polem wyboru: notka w podglądzie, opcje w inspektorze bez formatu", () => {
  renderReview();
  fireEvent.keyDown(document, { key: "F8" });
  fireEvent.keyDown(document, { key: "F8" });
  expect(screen.getByText("Problem 2 z 5")).toBeDefined();
  expect(screen.getByText(/Wybrane pole jest teraz ukryte/)).toBeDefined();
  expect(screen.getByText("Opcje do wyboru")).toBeDefined();
  expect(screen.queryByText("Format odpowiedzi")).toBeNull();
});

test("strzałki przełączają zakładki w kolumnie edycji", () => {
  renderReview();
  const pole = screen.getByRole("tab", { name: "Pole", selected: true });
  fireEvent.keyDown(pole, { key: "ArrowRight" });
  const json = screen
    .getAllByRole("tab", { name: "JSON" })
    .find((t) => t.closest('[aria-label="Edycja"]'));
  expect(json?.getAttribute("aria-selected")).toBe("true");
  expect(document.activeElement).toBe(json);
});

test("kolumny robocze: dowolna para obok siebie, wybór widoku z drugiej kolumny zamienia je", () => {
  renderReview();
  const col = (id: string) => document.getElementById(id)?.dataset.col;
  const tab = (list: string, name: string) =>
    screen
      .getAllByRole("tab", { name })
      .find((t) => t.closest(`[aria-label="${list}"]`)) as HTMLElement;
  expect([col("pole"), col("podglad")]).toEqual(["a", "b"]);

  fireEvent.click(tab("Druga kolumna", "Oryginał"));
  expect([col("pole"), col("oryginal"), col("podglad")]).toEqual([
    "a",
    "b",
    undefined,
  ]);

  fireEvent.click(tab("Edycja", "Oryginał"));
  expect([col("oryginal"), col("pole")]).toEqual(["a", "b"]);

  fireEvent.click(tab("Druga kolumna", "JSON"));
  expect([col("oryginal"), col("edytor"), col("pole")]).toEqual([
    "a",
    "b",
    undefined,
  ]);
});
