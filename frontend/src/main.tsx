import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";
import { App } from "./app/App";
import { routes } from "./app/routes";
import "../design/tokens.css";

const root = document.getElementById("root");
if (!root) throw new Error("Brak elementu #root w index.html");

createRoot(root).render(
  <StrictMode>
    <App router={createBrowserRouter(routes)} />
  </StrictMode>,
);
