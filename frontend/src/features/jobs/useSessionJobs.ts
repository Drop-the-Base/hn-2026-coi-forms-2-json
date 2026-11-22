import { useCallback, useState } from "react";

export type SessionJob = {
  id: string;
  fileName: string;
  uploadedAt: string;
  batchId?: string; // absent in lists saved before FR-E6
};

// The API has no job list, so the list lives in the tab for the session (ekrany.md §2).
const JOBS_KEY = "forms2json.jobs";

function readJobs(): SessionJob[] {
  try {
    const jobs: unknown = JSON.parse(sessionStorage.getItem(JOBS_KEY) ?? "[]");
    return Array.isArray(jobs) ? (jobs as SessionJob[]) : [];
  } catch {
    return []; // damaged or blocked storage: an empty list beats a blank page
  }
}

export function useSessionJobs() {
  const [jobs, setJobs] = useState(readJobs);
  const addJob = useCallback(
    (id: string, fileName: string, batchId: string) => {
      setJobs((current) => {
        const next = [
          { id, fileName, uploadedAt: new Date().toISOString(), batchId },
          ...current,
        ];
        try {
          sessionStorage.setItem(JOBS_KEY, JSON.stringify(next));
        } catch {
          // Full or blocked storage: the list still lives in this tab until it reloads.
        }
        return next;
      });
    },
    [],
  );
  return { jobs, addJob };
}
