import { render, screen } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { expect, test } from "vitest";
import { App } from "./App";
import { routes } from "./routes";

test("renderuje layout aplikacji", () => {
  render(<App router={createMemoryRouter(routes)} />);
  expect(
    screen.getByRole("heading", { name: "Formularze COI do JSON" }),
  ).toBeDefined();
});
