import type { UseQueryResult } from "@tanstack/react-query";
import { Link } from "react-router";
import type { JobStatus } from "../../shared/api/client";
import { POLL_SECONDS, STEPS, currentStep, type Steps } from "./api";
import { JobStatusText } from "./JobStatusText";
import "./JobProgress.css";

type StepView = "pending" | "running" | "done" | "failed";

const WORD: Record<StepView, string> = {
  pending: "oczekuje",
  running: "w toku",
  done: "zakończony",
  failed: "błąd",
};
const ICON: Record<StepView, string | null> = {
  pending: null,
  running: "i-loader",
  done: "i-check",
  failed: "i-x",
};

const clock = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString("pl-PL", { hour12: false });

/** " w 18 s", " w 1 min 9 s", or "" when a timestamp is missing (connected mid-step). */
function took(word: string, from?: number, to?: number) {
  if (from === undefined || to === undefined) return "";
  const s = to - from;
  if (s < 1)
    return ` ${word} ${Math.max(0.1, s).toLocaleString("pl-PL", { maximumFractionDigits: 1 })} s`;
  const r = Math.round(s);
  return ` ${word} ${r < 60 ? `${r} s` : `${Math.floor(r / 60)} min ${r % 60} s`}`;
}

/** Live pipeline register from design/postep.html (FR-T5): steps, loss of the stream, failure. */
export function JobProgress({
  status,
  steps,
  lost,
}: {
  status: UseQueryResult<JobStatus>;
  steps: Steps;
  lost: boolean;
}) {
  const failed = status.isError || status.data?.status === "failed";
  const current = currentStep(steps);
  const reached = STEPS.findIndex((step) => step === current);

  return (
    <div className="stack">
      {lost && !failed && (
        <div className="alert alert--warning" role="status">
          <span className="i i-refresh" aria-hidden="true"></span>
          <p className="alert__title">Utracono połączenie na żywo</p>
          <p>
            Przetwarzanie trwa dalej. Sprawdzamy stan co {POLL_SECONDS} sekundy
            {status.dataUpdatedAt > 0 &&
              `, ostatnio o ${clock(status.dataUpdatedAt / 1000)}`}
            .
          </p>
        </div>
      )}
      {failed && (
        <div className="alert alert--error" role="alert">
          <span className="i i-x-circle" aria-hidden="true"></span>
          <p className="alert__title">Nie udało się przetworzyć pliku</p>
          <p>
            {status.isError
              ? status.error.message
              : `Serwer przerwał pracę (${status.data?.error ?? "nieznany błąd"}).`}{" "}
            Plik jest już usunięty z serwera. Wgraj go ponownie albo wgraj inny
            plik.
          </p>
          <div className="alert__actions">
            <Link className="btn btn--secondary" to="/">
              <span className="i i-upload" aria-hidden="true"></span>Wgraj inny
              plik
            </Link>
          </div>
        </div>
      )}
      <section className="sheet" aria-labelledby="kroki-h">
        <div className="sheet__head">
          <h2 id="kroki-h">Przebieg</h2>
          {status.data?.status === "pending" && !lost ? (
            <span className="status status--running">
              <span className="i i-loader" aria-hidden="true"></span>Na żywo
            </span>
          ) : (
            <JobStatusText status={status} />
          )}
        </div>
        <div className="sheet__body">
          {/* Announces only step changes, not every re-render (ekrany.md §3). */}
          <p className="visually-hidden" aria-live="polite">
            {current &&
              `${current.label}: ${WORD[viewOf(steps, STEPS.indexOf(current), reached)]}.`}
          </p>
          {!current && !failed && (
            <p className="muted steps__wait">
              Zadanie czeka na swoją kolej albo trwa krok, który zaczął się,
              zanim otworzyłeś tę stronę. Kolejne kroki pojawią się tu same.
            </p>
          )}
          <ol className="steps">
            {STEPS.map((step, index) => {
              const state = steps[step.name];
              const view = viewOf(steps, index, reached);
              const icon = ICON[view];
              return (
                <li className="step" data-state={view} key={step.name}>
                  <span className="step__time">
                    {state?.startedAt
                      ? clock(state.startedAt)
                      : view === "done"
                        ? ""
                        : "czeka"}
                  </span>
                  <span className="step__rail">
                    <span className="step__dot">
                      {icon && (
                        <span className={`i ${icon}`} aria-hidden="true"></span>
                      )}
                    </span>
                    <span className="step__line"></span>
                  </span>
                  <div className="step__body">
                    <p className="step__title">
                      {step.label}{" "}
                      <span className="visually-hidden">({WORD[view]})</span>
                    </p>
                    <p className="step__msg">
                      {view === "done"
                        ? `Zakończono${took("w", state?.startedAt, state?.endedAt)}.`
                        : view === "failed"
                          ? `Przerwano${took("po", state?.startedAt, state?.endedAt)}.`
                          : step.hint}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </section>
    </div>
  );
}

/** Steps before the one reached have finished, even if their events came before we connected. */
function viewOf(steps: Steps, index: number, reached: number): StepView {
  const state = steps[STEPS[index].name];
  if (state?.status === "failed") return "failed";
  if (state?.status === "done" || index < reached) return "done";
  return state ? "running" : "pending";
}
