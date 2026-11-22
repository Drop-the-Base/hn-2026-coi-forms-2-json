import { Suspense } from "react";
import { Link, useParams } from "react-router";
import { ReviewScreen, useFormSchema } from "../review";
import { useJobEvents } from "./api";
import { JobProgress } from "./JobProgress";
import { useSessionJobs } from "./useSessionJobs";

export function JobResultPage() {
  const jobId = useParams().jobId ?? "";
  const { status, steps, lost } = useJobEvents(jobId);
  const schema = useFormSchema();
  const fileName = useSessionJobs().jobs.find(
    (job) => job.id === jobId,
  )?.fileName;

  const loading = (
    <main className="page">
      <p className="muted" role="status">
        Wczytywanie ekranu przeglądu…
      </p>
    </main>
  );
  if (status.data?.status === "done") {
    if (schema.isError)
      return (
        <main className="page page--narrow">
          <div className="alert alert--error" role="alert">
            <span className="i i-x-circle" aria-hidden="true"></span>
            <p>
              Nie udało się pobrać schematu eUsługi, więc nie da się sprawdzić
              wyniku.
            </p>
            <div className="alert__actions">
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => void schema.refetch()}
              >
                Spróbuj ponownie
              </button>
            </div>
          </div>
        </main>
      );
    if (!schema.data) return loading;
    return (
      <Suspense fallback={loading}>
        <ReviewScreen
          result={status.data.result}
          schema={schema.data}
          jobId={jobId}
          fileName={fileName}
        />
      </Suspense>
    );
  }

  // Progress until the job is done; then the review screen replaces this page (FR-T5).
  return (
    <main className="page page--narrow">
      <title>{`Postęp: ${fileName ?? "zadanie"} – JSON-jusz`}</title>
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
