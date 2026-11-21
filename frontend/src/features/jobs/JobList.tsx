import { Link } from "react-router";
import { formatTime } from "../../shared/api/token";
import { useJobStatus } from "./api";
import { JobStatusText } from "./JobStatusText";
import type { SessionJob } from "./useSessionJobs";
import "./JobList.css";

function JobRow({ job }: { job: SessionJob }) {
  const status = useJobStatus(job.id);
  return (
    <tr>
      <td>
        <span className="cell-file">
          <Link to={`/zadania/${job.id}`}>{job.fileName}</Link>
          <span className="mono">{job.id.slice(0, 8)}</span>
        </span>
      </td>
      <td className="num" data-label="Wgrano">
        {formatTime(new Date(job.uploadedAt))}
      </td>
      {/* aria-live announces only state changes, with the file name for context */}
      <td aria-live="polite" aria-atomic="true">
        <span className="visually-hidden">{job.fileName}: </span>
        <JobStatusText status={status} />
      </td>
      <td className="row-actions">
        {status.data?.status === "done" && (
          <Link
            className="btn btn--secondary btn--sm"
            to={`/zadania/${job.id}`}
          >
            Zobacz wynik
            <span className="visually-hidden">: {job.fileName}</span>
          </Link>
        )}
      </td>
    </tr>
  );
}

export function JobList({ jobs }: { jobs: SessionJob[] }) {
  return (
    <section className="sheet" aria-labelledby="lista-h" id="lista">
      <div className="sheet__head">
        <h2 id="lista-h">Twoje zadania</h2>
      </div>
      {jobs.length === 0 ? (
        <div className="empty">
          <h3>Nie masz jeszcze zadań</h3>
          <p>
            Wgraj blankiet formularza w sekcji powyżej. Zadanie pojawi się tutaj
            od razu, a wynik za kilkadziesiąt sekund do kilku minut, zależnie od
            liczby stron.
          </p>
        </div>
      ) : (
        <div className="table-wrap jobs-wrap">
          <table className="table jobs" aria-labelledby="lista-h">
            <thead>
              <tr>
                <th scope="col">Plik</th>
                <th scope="col" className="num">
                  Wgrano
                </th>
                <th scope="col">Stan</th>
                <th scope="col">
                  <span className="visually-hidden">Akcje</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <JobRow key={job.id} job={job} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
