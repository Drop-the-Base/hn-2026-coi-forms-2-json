import { Suspense } from "react";
import { Link, useParams } from "react-router";
import { ReviewScreen } from "../review";
import { useJobStatus } from "./api";
import { JobStatusText } from "./JobStatusText";
import { useSessionJobs } from "./useSessionJobs";

export function JobResultPage() {
  const jobId = useParams().jobId ?? "";
  const status = useJobStatus(jobId);
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
      <section className="sheet" aria-labelledby="wynik-h">
        <div className="sheet__head">
          <h2 id="wynik-h">Wynik</h2>
          <span aria-live="polite">
            <JobStatusText status={status} />
          </span>
        </div>
        <div className="sheet__body">
          <p className="muted">
            {status.isError || status.data?.status === "failed"
              ? "Brak wyniku. Wgraj plik ponownie na liście zadań."
              : "Przetwarzanie trwa. Wynik pojawi się tutaj sam, nie musisz odświeżać strony."}
          </p>
        </div>
      </section>
    </main>
  );
}
