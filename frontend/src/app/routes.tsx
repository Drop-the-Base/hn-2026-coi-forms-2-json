import { Navigate, type RouteObject } from "react-router";
import { LoginPage } from "../features/auth";
import { JobResultPage } from "../features/jobs";
import { ErrorPage } from "./ErrorPage";
import { Layout } from "./Layout";
import { TasksPage } from "./TasksPage";

export const routes: RouteObject[] = [
  {
    // Pathless parent: a render error anywhere below gets a fallback, not React Router's dev page.
    errorElement: <ErrorPage />,
    children: [
      { path: "/logowanie", element: <LoginPage /> },
      {
        path: "/",
        element: <Layout />,
        children: [
          { index: true, element: <TasksPage /> },
          { path: "zadania/:jobId", element: <JobResultPage /> },
        ],
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
];
