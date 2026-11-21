import { useState } from "react";
import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { RouterProvider, type DataRouter } from "react-router";
import { ApiError } from "../shared/api/client";
import { clearToken, getToken, tokenProblem } from "../shared/api/token";

export function App({ router }: { router: DataRouter }) {
  const [queryClient] = useState(() => {
    // Any 401 ends the session: back to login with the reason (ekrany.md §1).
    const onError = (error: Error) => {
      const token = getToken();
      // No token: another request already handled this 401.
      if (!(error instanceof ApiError) || error.status !== 401 || !token)
        return;
      const message =
        tokenProblem(token) ??
        "Serwer nie przyjął tokenu. Sprawdź, czy wkleiłeś go w całości.";
      clearToken();
      client.clear();
      void router.navigate("/logowanie", { state: { error: message } });
    };
    const client: QueryClient = new QueryClient({
      queryCache: new QueryCache({ onError }),
      mutationCache: new MutationCache({ onError }),
      defaultOptions: {
        queries: {
          // 4xx (bad token, unknown job) will not change on retry.
          retry: (count, error) =>
            !(
              error instanceof ApiError &&
              error.status >= 400 &&
              error.status < 500
            ) && count < 3,
        },
      },
    });
    return client;
  });
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
