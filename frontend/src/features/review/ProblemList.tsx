import { useState } from "react";
import { ConfidenceBadge } from "../../shared/confidence";
import { isUncertain, type Problem } from "./review";

export type Filter = "all" | "error" | "uncertain";

const SHOWN: Record<Filter, (p: Problem) => boolean> = {
  all: () => true,
  error: (p) => p.kind === "error",
  uncertain: isUncertain,
};

export function ProblemKind({ problem }: { problem: Problem }) {
  return problem.kind === "error" ? (
    <span className="issue__kind issue__kind--error">
      <span className="i i-x-circle" aria-hidden="true"></span>Błąd
    </span>
  ) : (
    <span className="issue__kind issue__kind--check">
      <span className="i i-alert" aria-hidden="true"></span>Do sprawdzenia
    </span>
  );
}

interface Props {
  problems: Problem[];
  current: number | null;
  describe: (path: string) => string;
  onSelect: (index: number) => void;
}

/** Problem list with a filter (ekran-przegladu.md §4); the index passed up is in the unfiltered list. */
export function ProblemList({ problems, current, describe, onSelect }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  return (
    <>
      <div className="pane__head">
        <h2 id="problemy-h">
          Problemy <span className="num">({problems.length})</span>
        </h2>
        {problems.length > 0 && (
          <div className="end">
            <label className="visually-hidden" htmlFor="filtr">
              Pokaż
            </label>
            <select
              className="select"
              id="filtr"
              value={filter}
              onChange={(e) => setFilter(e.target.value as Filter)}
            >
              <option value="all">Wszystkie</option>
              <option value="error">Błędy</option>
              <option value="uncertain">Niska pewność</option>
            </select>
          </div>
        )}
      </div>
      <div className="pane__body">
        {problems.length === 0 ? (
          <div className="review-empty">
            <p>
              <strong>Nic do poprawy</strong>
            </p>
            <p className="muted">
              Gdy zmienisz JSON, błędy schematu pokaże pasek pod edytorem.
            </p>
          </div>
        ) : (
          <ol className="issues">
            {problems.map(
              (problem, i) =>
                SHOWN[filter](problem) && (
                  <li key={i}>
                    <button
                      className="issue"
                      type="button"
                      aria-current={i === current ? "true" : undefined}
                      onClick={() => onSelect(i)}
                    >
                      <span className="issue__row">
                        <ProblemKind problem={problem} />
                        {isUncertain(problem) && (
                          <ConfidenceBadge value={problem.confidence} />
                        )}
                      </span>
                      <span>{problem.message}</span>
                      <span className="issue__path">
                        {describe(problem.path)}
                      </span>
                    </button>
                  </li>
                ),
            )}
          </ol>
        )}
      </div>
      <div className="pane__foot muted">
        <kbd>F8</kbd> następny problem, <kbd>Shift</kbd>+<kbd>F8</kbd> poprzedni
      </div>
    </>
  );
}
