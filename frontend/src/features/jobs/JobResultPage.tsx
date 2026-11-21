import { Link, useParams } from "react-router";
import { useJobEvents } from "./api";
import { JobProgress } from "./JobProgress";
import { JobStatusText } from "./JobStatusText";
import { useSessionJobs } from "./useSessionJobs";
import "./JobResultPage.css";

// shortcut: raw JSON only; the review screen (editor, preview, problems) comes in #52-#54.
export function JobResultPage() {
  const jobId = useParams().jobId ?? "";
  const { status, steps, lost } = useJobEvents(jobId);
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
      {/* Progress until the job is done, then the result in the same place (FR-T5). */}
      {status.data?.status === "done" ? (
        <section className="sheet" aria-labelledby="wynik-h">
          <div className="sheet__head">
            <h2 id="wynik-h">Wynik</h2>
            <JobStatusText status={status} />
          </div>
          <div className="sheet__body">
            <pre className="result-json" tabIndex={0} aria-label="Wynik JSON">
              {JSON.stringify(status.data.result, null, 2)}
            </pre>
          </div>
        </section>
      ) : (
        <JobProgress status={status} steps={steps} lost={lost} />
      )}
    </main>
  );
}
