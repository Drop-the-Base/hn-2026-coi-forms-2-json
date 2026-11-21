import { useQuery } from "@tanstack/react-query";
import { getJob } from "../../shared/api/client";

export const useJobStatus = (jobId: string) =>
  useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    // shortcut: polling every 2 s until the job ends; switch to SSE GET /jobs/{id}/events (ADR-0014, #37) with polling as fallback.
    refetchInterval: (query) =>
      query.state.data?.status === "pending" ? 2000 : false,
  });
