import { useEffect, useState } from "react";
import { skipToken, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJob, getJobEvents } from "../../shared/api/client";
import { readSse } from "./sse";

/** Pipeline steps in order, as named in the SSE events (architecture.md §4). */
export const STEPS = [
  {
    name: "ingest",
    label: "Odczyt pliku",
    hint: "Tekst, tabele i pola wyboru z pliku.",
  },
  {
    name: "understand",
    label: "Analiza treści przez model",
    hint: "Pola, warunki i zgody. Najdłuższy krok, zwykle od 1 do 5 minut.",
  },
  {
    name: "compose",
    label: "Budowa formularza",
    hint: "Strony, sekcje i bloki ze Standardów.",
  },
  {
    name: "validate",
    label: "Sprawdzenie reguł",
    hint: "Reguły techniczne, Standardy i schemat JSON.",
  },
  {
    name: "report",
    label: "Raport",
    hint: "Ocena pewności i lista elementów do sprawdzenia.",
  },
] as const;

export type StepState = {
  status: "started" | "done" | "failed";
  startedAt?: number;
  endedAt?: number;
};
export type Steps = Partial<Record<string, StepState>>;

/** One SSE event (PR #101). The OpenAPI schema does not describe the stream body. */
type JobEvent = {
  step: string;
  status: "started" | "done" | "failed" | "progress";
  ts: number;
};

export const POLL_SECONDS = 2;
const RECONNECT_MS = 5000;

const useJobStatus = (jobId: string, poll = true) =>
  useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) =>
      poll && query.state.data?.status === "pending"
        ? POLL_SECONDS * 1000
        : false,
  });

/**
 * Job status plus live steps from SSE (ADR-0014). Polls only while the stream is down
 * (`lost`) or when `live` is off, and keeps reconnecting in the background.
 * Steps live in the query cache, so the job list and the job page share them.
 */
export function useJobEvents(jobId: string, live = true) {
  const queryClient = useQueryClient();
  const [lost, setLost] = useState(false);
  const status = useJobStatus(jobId, !live || lost);
  const stepsKey = ["job", jobId, "steps"];
  const steps = useQuery<Steps>({
    queryKey: stepsKey,
    queryFn: skipToken,
  }).data;
  const pending = status.data?.status === "pending";

  useEffect(() => {
    if (!live || !pending) return;
    const abort = new AbortController();
    const key = ["job", jobId, "steps"];
    const refetchStatus = () =>
      void queryClient.invalidateQueries({ queryKey: ["job", jobId] });

    async function connect() {
      const response = await getJobEvents(jobId, abort.signal);
      // The status query hits the same 401/404 and handles it like everywhere else.
      if (response.status === 401 || response.status === 404) return "stop";
      if (!response.ok || !response.body) return "lost";
      for await (const data of readSse(response.body)) {
        const event = JSON.parse(data) as JobEvent;
        setLost(false);
        if (event.status === "progress") continue; // "job is running", sent first
        if (event.step === "job") return "stop"; // final event: done or failed
        const { step, status, ts } = event;
        queryClient.setQueryData<Steps>(key, (old = {}) => ({
          ...old,
          [step]:
            status === "started"
              ? { status, startedAt: ts }
              : { ...old[step], status, endedAt: ts },
        }));
      }
      return "lost"; // stream closed before the final event
    }

    void (async () => {
      while (!abort.signal.aborted) {
        const outcome = await connect().catch(() => "lost");
        if (abort.signal.aborted) return;
        if (outcome === "stop") return refetchStatus();
        setLost(true);
        await new Promise((resolve) => setTimeout(resolve, RECONNECT_MS));
      }
    })();
    return () => abort.abort();
  }, [jobId, live, pending, queryClient]);

  return { status, steps: steps ?? {}, lost };
}

/** The step the pipeline reached last, or undefined before the first event. */
export const currentStep = (steps: Steps) =>
  [...STEPS].reverse().find((step) => steps[step.name]);
