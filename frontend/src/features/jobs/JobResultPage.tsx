import { Suspense } from "react";
import { Link, useParams } from "react-router";
import { ReviewScreen } from "../review";
import { useJobEvents } from "./api";
import { JobProgress } from "./JobProgress";
import { useSessionJobs } from "./useSessionJobs";

export function JobResultPage() {
  const jobId = useParams().jobId ?? "";
  const { status, steps, lost } = useJobEvents(jobId);
  const fileName = useSessionJobs().jobs.find(
    (job) => job.id === jobId,
  )?.fileName;

  if (status.data?.status === "done")
    return (
      <Suspense
        fallback={
          <main className="page">
            <p className="muted" role="status">
              Wczytywanie ekranu przeglądu…
            </p>
          </main>
        }
      >
        <ReviewScreen
          result={status.data.result}
          jobId={jobId}
          fileName={fileName}
        />
      </Suspense>
    );

  // Progress until the job is done; then the review screen replaces this page (FR-T5).
  return (
    <main className="page page--narrow">
      <div className="page-head">
        <div>
          <Link className="back" to="/">
            <span className="i i-arrow-left" aria-hidden="true"></span>Zadania
          </Link>
          <h1>{fileName ?? "Wynik zadania"}</h1>
          <p className="page-head__meta mono">{jobId}</p>
        </div>
      </div>
      <JobProgress status={status} steps={steps} lost={lost} />
    </main>
  );
}
