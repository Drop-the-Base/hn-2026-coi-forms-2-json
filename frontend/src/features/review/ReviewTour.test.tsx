import { fireEvent, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { expect, test } from "vitest";
import { axeViolations } from "../../test/axe";
import { FORM_SCHEMA } from "../../test/server";
import ReviewPage from "./ReviewScreen";
import { place } from "./ReviewTour";
import wynik from "./fixtures/wynik-wzorzec-1.json";

// One file, one page load: the order matters, the prompt shows only until it is answered.

function renderReview() {
  const router = createMemoryRouter([
    {
      path: "*",
      element: (
        <ReviewPage
          result={wynik}
          schema={FORM_SCHEMA}
          jobId="b6af199b-0000-4000-8000-000000000001"
          fileName="wniosek.pdf"
        />
      ),
    },
  ]);
  return render(<RouterProvider router={router} />);
}

const dialog = () => screen.queryByRole("dialog");
// Inside the open dialog, if any: the preview has its own "Dalej".
const button = (name: string | RegExp) =>
  within(dialog() ?? document.body).getByRole("button", { name });

test("pytanie o samouczek: z liczbą kroków, Pomiń zamyka i nie wraca w tej sesji strony", () => {
  const { unmount } = renderReview();
  expect(dialog()?.textContent).toContain("Pierwszy raz na tym ekranie?");
  expect(document.activeElement).toBe(button("Pokaż samouczek (7 kroków)"));
  fireEvent.click(button("Pomiń"));
  expect(dialog()).toBeNull();

  unmount();
  renderReview();
  expect(dialog()).toBeNull();
});

test("samouczek: Dalej, Wstecz, Zakończ, Esc i powrót fokusu do przycisku", () => {
  renderReview();
  const restart = button("Samouczek");
  restart.focus();
  fireEvent.click(restart);
  expect(dialog()?.getAttribute("aria-labelledby")).toBe("tour-h");
  expect(screen.getByText("Krok 1 z 7")).toBeDefined();
  expect(screen.getByRole("heading", { name: "Ocena ogólna" })).toBeDefined();
  expect((button("Wstecz") as HTMLButtonElement).disabled).toBe(true);
  expect(document.activeElement).toBe(button("Dalej"));

  fireEvent.click(button("Dalej"));
  expect(screen.getByText("Krok 2 z 7")).toBeDefined();
  expect(screen.getByText(/poniżej 0,85/)).toBeDefined();
  fireEvent.click(button("Wstecz"));
  expect(screen.getByText("Krok 1 z 7")).toBeDefined();
  for (let i = 0; i < 6; i++) fireEvent.click(button("Dalej"));
  expect(screen.getByRole("heading", { name: "Pobranie" })).toBeDefined();
  fireEvent.click(button("Zakończ"));
  expect(dialog()).toBeNull();
  expect(document.activeElement).toBe(restart);

  fireEvent.click(restart);
  fireEvent.click(button("Dalej"));
  fireEvent.keyDown(document.activeElement as Element, { key: "Escape" });
  expect(dialog()).toBeNull();
  expect(document.activeElement).toBe(restart);
});

test("samouczek bez błędów WCAG", async () => {
  renderReview();
  fireEvent.click(button("Samouczek"));
  fireEvent.click(button("Dalej"));
  expect(await axeViolations()).toEqual([]);
});

test("karta staje pod celem, nad nim, obok albo w jego rogu", () => {
  const card = [300, 200] as const;
  const box = (top: number, left: number, bottom: number, right: number) => ({
    top,
    left,
    bottom,
    right,
  });
  // small target at the top: below it
  expect(place(box(10, 100, 50, 200), ...card, 1280, 720)).toEqual({
    top: 62,
    left: 100,
  });
  // target at the bottom: above it
  expect(place(box(600, 100, 700, 200), ...card, 1280, 720)).toEqual({
    top: 388,
    left: 100,
  });
  // full-height column on the left: right of it
  expect(place(box(0, 0, 720, 400), ...card, 1280, 720)).toEqual({
    top: 16,
    left: 412,
  });
  // whole screen: inside its bottom-right corner
  expect(place(box(0, 0, 720, 1280), ...card, 1280, 720)).toEqual({
    top: 504,
    left: 964,
  });
});
