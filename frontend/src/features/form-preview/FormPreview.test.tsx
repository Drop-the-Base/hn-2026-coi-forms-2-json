import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { FormPreview } from "./FormPreview";
import { pageOrder, type FormField, type FormJson } from "./form";
import wzorzec1 from "./fixtures/wzorzec-1.json";
import wzorzec5 from "./fixtures/wzorzec-5.json";

afterEach(cleanup);

test.each([
  ["wzorzec 1", wzorzec1 as FormJson],
  ["wzorzec 5", wzorzec5 as FormJson],
])("renderuje %s ze stronami według flow", async (_, form) => {
  render(<FormPreview form={form} />);
  expect(screen.getByRole("heading", { level: 2 }).textContent).toBe(
    form.title,
  );
  expect(screen.getAllByRole("button", { name: /^Strona \d, / })).toHaveLength(
    4,
  );
  expect(screen.getByRole("heading", { level: 3 }).textContent).toBe("Dane");
  // Kraj = Polska by default, so the Polish address fields appear after evaluation.
  expect((await screen.findAllByLabelText("Kod pocztowy")).length).toBe(1);
});

test("przechodzi między stronami przyciskami i krokami", () => {
  render(<FormPreview form={wzorzec5 as FormJson} />);
  fireEvent.click(screen.getByRole("button", { name: "Dalej" }));
  expect(screen.getByRole("heading", { level: 3 }).textContent).toBe(
    "Informacje o nadpłacie",
  );
  expect(
    screen
      .getByRole("button", { name: "Strona 2, Informacje o nadpłacie" })
      .getAttribute("aria-current"),
  ).toBe("step");

  fireEvent.click(
    screen.getByRole("button", { name: "Strona 4, Strona końcowa" }),
  );
  expect(screen.queryByRole("button", { name: "Dalej" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Wróć" }));
  expect(screen.getByRole("heading", { level: 3 }).textContent).toBe(
    "Kontakt i zgody",
  );
});

test("kolejność stron wynika z flow, nie z kolejności tabs", () => {
  const form = wzorzec1 as FormJson;
  const reversed = { ...form, tabs: [...form.tabs].reverse() };
  expect(pageOrder(reversed).tabs.map((t) => t.title)).toEqual([
    "Dane",
    "Informacje o budynku",
    "Kontakt z urzędem",
    "Strona końcowa",
  ]);
  const broken = { ...form, flow: { links: form.flow.links.slice(1) } };
  expect(pageOrder(broken).consistent).toBe(false);
});

test("pole wymagane ma required, readOnly ma readonly, nieznany typ jest opisany", () => {
  const field = (f: Partial<FormField>, y = 0) => ({
    x: 0,
    y,
    rows: 1,
    cols: 3,
    field: { id: "", type: "TEXT_FIELD", title: "", ...f },
  });
  const form: FormJson = {
    title: "Test",
    flow: { links: [] },
    tabs: [
      {
        id: "t1",
        title: "Strona",
        type: "MAIN",
        questions: [
          field({ id: "a", title: "Imię", validation: ["REQUIRED"] }),
          field({ id: "b", title: "Urząd", readOnly: true }, 1),
          field({ id: "c", type: "MAP", title: "Mapa" }, 2),
        ],
      },
    ],
  };
  render(<FormPreview form={form} />);
  expect(
    (screen.getByLabelText("Imię (wymagane)") as HTMLInputElement).required,
  ).toBe(true);
  expect((screen.getByLabelText("Urząd") as HTMLInputElement).readOnly).toBe(
    true,
  );
  screen.getByText("Nieobsługiwany typ pola: MAP");
});

test("warunek SHOW (JSONata) pokazuje i ukrywa sekcję po odpowiedzi", async () => {
  render(<FormPreview form={wzorzec1 as FormJson} />);
  await screen.findAllByLabelText("Kod pocztowy");
  expect(
    screen.queryByRole("heading", { name: "Dane innej osoby" }),
  ).toBeNull();

  fireEvent.click(screen.getByLabelText("Innej osoby"));
  await screen.findByRole("heading", { name: "Dane innej osoby" });

  fireEvent.click(screen.getByLabelText("Swoim"));
  await expect
    .poll(() => screen.queryByRole("heading", { name: "Dane innej osoby" }))
    .toBeNull();
});
