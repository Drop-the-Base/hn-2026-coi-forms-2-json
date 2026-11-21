import type { UseQueryResult } from "@tanstack/react-query";
import type { JobStatus } from "../../shared/api/client";

/** One line of job state with icon and word, never colour alone (NFR-15). */
export function JobStatusText({
  status,
  step,
}: {
  status: UseQueryResult<JobStatus>;
  /** Label of the current pipeline step, shown while the job runs. */
  step?: string;
}) {
  if (status.isError)
    return (
      <span className="status status--failed">
        <span className="i i-x-circle" aria-hidden="true"></span>Błąd:{" "}
        {status.error.message}
      </span>
    );
  if (status.data?.status === "done")
    return (
      <span className="status status--done">
        <span className="i i-check-circle" aria-hidden="true"></span>Gotowe
      </span>
    );
  if (status.data?.status === "failed")
    return (
      <span className="status status--failed">
        <span className="i i-x-circle" aria-hidden="true"></span>Błąd:{" "}
        {status.data.error}
      </span>
    );
  return status.data ? (
    <span className="status status--running">
      <span className="i i-loader" aria-hidden="true"></span>W toku
      {step && `: ${step}`}
    </span>
  ) : (
    <span className="status status--queued">
      <span className="i i-clock" aria-hidden="true"></span>Sprawdzamy stan…
    </span>
  );
}
