import { Navigate, type RouteObject } from "react-router";
import { LoginPage } from "../features/auth";
import { JobResultPage } from "../features/jobs";
import { Layout } from "./Layout";
import { TasksPage } from "./TasksPage";

export const routes: RouteObject[] = [
  { path: "/logowanie", element: <LoginPage /> },
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <TasksPage /> },
      { path: "zadania/:jobId", element: <JobResultPage /> },
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
  { path: "*", element: <Navigate to="/" replace /> },
];
