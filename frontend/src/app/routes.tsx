import type { RouteObject } from "react-router";
import { Layout } from "./Layout";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        // shortcut: dev-only preview of reference forms until #54 shows the job result.
        // Lazy, so the 200 kB fixtures stay out of the main bundle.
        path: "podglad-demo",
        lazy: async () => ({
          Component: (await import("../features/form-preview")).FormPreviewDemo,
        }),
      },
    ],
  },
];
