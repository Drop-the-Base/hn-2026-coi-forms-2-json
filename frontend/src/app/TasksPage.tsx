import { JobList, useSessionJobs } from "../features/jobs";
import { UploadPanel } from "../features/upload";

export function TasksPage() {
  const { jobs, addJob } = useSessionJobs();
  return (
    <>
      <title>Zadania – forms2json</title>
      <a className="skip" href="#lista">
        Przejdź do listy zadań
      </a>
      <main className="page stack">
        <div className="page-head">
          <div>
            <h1>Zadania</h1>
            <p className="page-head__meta">
              Wyniki są na serwerze tylko tymczasowo. Lista zadań znika po
              zamknięciu karty.
            </p>
          </div>
        </div>
        <UploadPanel onUploaded={addJob} />
        <JobList jobs={jobs} />
      </main>
    </>
  );
}
