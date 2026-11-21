import { Link, useParams } from "react-router";
import { useJobStatus } from "./api";
import { JobStatusText } from "./JobStatusText";
import { useSessionJobs } from "./useSessionJobs";
import "./JobResultPage.css";

// shortcut: raw JSON only; the review screen (editor, preview, problems) comes in #52-#54.
export function JobResultPage() {
  const jobId = useParams().jobId ?? "";
  const status = useJobStatus(jobId);
  const fileName = useSessionJobs().jobs.find(
    (job) => job.id === jobId,
  )?.fileName;

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
          {status.data?.status === "done" ? (
            <pre className="result-json" tabIndex={0} aria-label="Wynik JSON">
              {JSON.stringify(status.data.result, null, 2)}
            </pre>
          ) : (
            <p className="muted">
              {status.isError || status.data?.status === "failed"
                ? "Brak wyniku. Wgraj plik ponownie na liście zadań."
                : "Przetwarzanie trwa. Wynik pojawi się tutaj sam, nie musisz odświeżać strony."}
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
