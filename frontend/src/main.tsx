// Base styles first, so feature CSS of equal specificity wins (as in the prototypes).
import "./styles/ui.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";
import { App } from "./app/App";
import { routes } from "./app/routes";

const root = document.getElementById("root");
if (!root) throw new Error("Brak elementu #root w index.html");

createRoot(root).render(
  <StrictMode>
    <App router={createBrowserRouter(routes)} />
  </StrictMode>,
);
