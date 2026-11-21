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
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
];
