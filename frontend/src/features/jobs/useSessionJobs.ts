import { useCallback, useState } from "react";

export type SessionJob = {
  id: string;
  fileName: string;
  uploadedAt: string;
  batchId?: string; // absent in lists saved before FR-E6
};

// The API has no job list, so the list lives in the tab for the session (ekrany.md §2).
const JOBS_KEY = "forms2json.jobs";

const readJobs = (): SessionJob[] =>
  JSON.parse(sessionStorage.getItem(JOBS_KEY) ?? "[]") as SessionJob[];

export function useSessionJobs() {
  const [jobs, setJobs] = useState(readJobs);
  const addJob = useCallback(
    (id: string, fileName: string, batchId: string) => {
      setJobs((current) => {
        const next = [
          { id, fileName, uploadedAt: new Date().toISOString(), batchId },
          ...current,
        ];
        sessionStorage.setItem(JOBS_KEY, JSON.stringify(next));
        return next;
      });
    },
    [],
  );
  return { jobs, addJob };
}
