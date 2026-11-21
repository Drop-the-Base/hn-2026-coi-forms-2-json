import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { FormPreview, type FormJson } from "../form-preview";
import {
  ConfidenceBadge,
  confidenceLevel,
  formatConfidence,
} from "../../shared/confidence";
import { JsonEditor, type JsonEditorHandle } from "./JsonEditor";
import { PreviewBoundary } from "./PreviewBoundary";
import { ProblemKind, ProblemList } from "./ProblemList";
import { SourceView } from "./SourceView";
import {
  buildProblems,
  checkJson,
  describePath,
  downloadName,
  isUncertain,
  plural,
  asReviewResult,
  type ReviewResult,
} from "./review";
import "./ReviewScreen.css";

type Pane = "podglad" | "oryginal" | "edytor" | "problemy";
type Right = "podglad" | "oryginal";

const LEVEL_WORD = { low: "niska", medium: "średnia", high: "wysoka" };

interface Props {
  result: ReviewResult;
  jobId: string;
  fileName?: string;
}

/** Review of a finished job; default export for React.lazy, so CodeMirror and jsonata load with this screen only. */
export default function ReviewPage(
  props: Omit<Props, "result"> & { result: unknown },
) {
  const result = asReviewResult(props.result);
  return result ? (
    <ReviewScreen {...props} result={result} />
  ) : (
    <main className="page page--narrow">
      <div className="alert alert--error" role="alert">
        <span className="i i-x-circle" aria-hidden="true"></span>
        <p>
          Wynik zadania ma nieoczekiwany format, więc nie da się go przejrzeć.
          Wgraj plik ponownie.
        </p>
      </div>
    </main>
  );
}

/** Review screen (FR-T1, FR-T2, FR-E5): problems | JSON editor | form preview. Design: design/przeglad.html. */
function ReviewScreen({ result, jobId, fileName }: Props) {
  const initial = useMemo(
    () => JSON.stringify(result.form, null, 2),
    [result.form],
  );
  const problems = useMemo(() => buildProblems(result), [result]);
  const editorRef = useRef<JsonEditorHandle>(null);
  const [text, setText] = useState(initial);
  const check = useMemo(() => checkJson(text), [text]);
  const valid = check.data !== undefined && check.schemaErrors.length === 0;
  const diagnostics = useMemo(
    () =>
      check.syntaxError
        ? [
            {
              from: check.syntaxError.from,
              to: check.syntaxError.from + 1,
              severity: "error" as const,
              message: "Błąd składni",
            },
          ]
        : check.schemaErrors.map((e) => ({
            from: e.from,
            to: e.from + 1,
            severity: "error" as const,
            message: e.message,
          })),
    [check],
  );

  // The preview keeps the last JSON that passed the schema (ekran-przegladu.md §6).
  const [form, setForm] = useState<FormJson>(result.form);
  if (valid && check.data !== form) setForm(check.data as FormJson);

  const [current, setCurrent] = useState<number | null>(null);
  const [selection, setSelection] = useState<{ path: string } | null>(null);
  const [pane, setPane] = useState<Pane>("podglad");
  // The right column on a wide screen; on a narrow one every pane is its own tab.
  const [right, setRight] = useState<Right>("podglad");
  const show = (id: Pane) => {
    setPane(id);
    if (id === "podglad" || id === "oryginal") setRight(id);
  };
  const [announcement, setAnnouncement] = useState("");
  const describe = (path: string) => describePath(form, path);

  function go(index: number, wrapped = false) {
    const problem = problems[index];
    setCurrent(index);
    setSelection({ path: problem.path });
    setPane("edytor");
    // After the render that shows the editor pane on a narrow screen.
    requestAnimationFrame(() => {
      const found = editorRef.current?.reveal(problem.path) ?? false;
      const confidence =
        problem.confidence === undefined
          ? ""
          : `, pewność ${LEVEL_WORD[confidenceLevel(problem.confidence)]} ${formatConfidence(problem.confidence)}`;
      setAnnouncement(
        `${wrapped ? "To był ostatni problem. Wracam do pierwszego. " : ""}Problem ${index + 1} z ${problems.length}: ${problem.message} ${describe(problem.path)}${confidence}.${found ? "" : " Elementu nie ma już w JSON-ie."}`,
      );
    });
  }
  const step = (delta: 1 | -1) => {
    if (!problems.length) return;
    const n = problems.length;
    const next =
      current === null ? (delta > 0 ? 0 : n - 1) : (current + delta + n) % n;
    go(next, delta > 0 && current === n - 1);
  };

  const onKey = useEffectEvent((e: KeyboardEvent) => {
    if (e.key !== "F8") return;
    e.preventDefault();
    step(e.shiftKey ? -1 : 1);
  });
  useEffect(() => {
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function download() {
    const blob = new Blob([editorRef.current?.text() ?? text], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = downloadName(form.title);
    link.click();
    setTimeout(() => URL.revokeObjectURL(url));
  }

  const errors = problems.filter((p) => p.kind === "error").length;
  const checks = problems.length - errors;
  const blocked = check.syntaxError
    ? "Popraw błąd składni, aby pobrać."
    : check.schemaErrors.length
      ? `Popraw ${plural(check.schemaErrors.length, ["błąd schematu", "błędy schematu", "błędów schematu"])}, aby pobrać.`
      : "";
  const problem = current === null ? null : problems[current];
  const paneProps = (id: Pane) => ({
    id,
    className: "pane",
    "aria-labelledby": `${id}-h`,
    "data-hidden": pane !== id || undefined,
    "data-off":
      (id === "podglad" || id === "oryginal") && right !== id
        ? true
        : undefined,
  });

  return (
    <main className="review">
      <a className="skip" href="#edytor">
        Przejdź do edytora
      </a>
      <div className="rhead">
        <div>
          <Link className="back" to="/">
            <span className="i i-arrow-left" aria-hidden="true"></span>Zadania
          </Link>
          <h1>{form.title || "Formularz bez tytułu"}</h1>
          <p className="page-head__meta">
            {fileName && `${fileName}, `}
            <span className="mono">{jobId.slice(0, 8)}</span>
          </p>
        </div>
        <div className="rhead__summary">
          <span>
            Ocena ogólna <ConfidenceBadge value={result.confidence.overall} />
          </span>
          <span>
            {problems.length === 0
              ? "Brak problemów"
              : [
                  errors && plural(errors, ["błąd", "błędy", "błędów"]),
                  checks && `${checks} do sprawdzenia`,
                ]
                  .filter(Boolean)
                  .join(", ")}
          </span>
          <div className="rhead__dl">
            <button
              className="btn btn--primary"
              type="button"
              disabled={Boolean(blocked)}
              aria-describedby={blocked ? "dl-why" : undefined}
              onClick={download}
            >
              <span className="i i-download" aria-hidden="true"></span>Pobierz
              JSON
            </button>
            {blocked && (
              <span className="btn-note" id="dl-why">
                {blocked}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="band" role="region" aria-label="Bieżący problem">
        <div className="band__in">
          {problems.length === 0 ? (
            <>
              <span className="band__kind band__kind--ok">
                <span className="i i-check-circle" aria-hidden="true"></span>
                Brak problemów do sprawdzenia
              </span>
              <p className="band__msg">
                Wszystkie elementy mają wysoką pewność i spełniają reguły.
                Przejrzyj podgląd i pobierz JSON.
              </p>
            </>
          ) : (
            <>
              <span className="band__pos">
                {problem
                  ? `Problem ${(current ?? 0) + 1} z ${problems.length}`
                  : plural(problems.length, [
                      "problem",
                      "problemy",
                      "problemów",
                    ])}
              </span>
              {problem ? (
                <>
                  <ProblemKind problem={problem} />
                  <p className="band__msg">
                    {problem.message}{" "}
                    <span className="path">{describe(problem.path)}</span>
                  </p>
                  {isUncertain(problem) && (
                    <ConfidenceBadge value={problem.confidence} />
                  )}
                </>
              ) : (
                <p className="band__msg">
                  Zacznij od pierwszego: <kbd>F8</kbd> albo „Następny”.
                </p>
              )}
              <div className="band__nav">
                <button
                  className="btn btn--secondary btn--sm"
                  type="button"
                  aria-keyshortcuts="Shift+F8"
                  onClick={() => step(-1)}
                >
                  <span className="i i-chevron-left" aria-hidden="true"></span>
                  Poprzedni
                </button>
                <button
                  className="btn btn--secondary btn--sm"
                  type="button"
                  aria-keyshortcuts="F8"
                  onClick={() => step(1)}
                >
                  Następny
                  <span className="i i-chevron-right" aria-hidden="true"></span>
                </button>
              </div>
            </>
          )}
        </div>
        <p className="visually-hidden" aria-live="polite">
          {announcement}
        </p>
      </div>

      <div className="tabs ws-tabs" role="tablist" aria-label="Obszary pracy">
        {(
          [
            ["podglad", "i-eye", "Podgląd"],
            ["edytor", "i-braces", "JSON"],
            ["oryginal", "i-file", "Oryginał"],
            ["problemy", "i-list", "Problemy"],
          ] as const
        ).map(([id, icon, label]) => (
          <button
            key={id}
            className="tab"
            role="tab"
            type="button"
            aria-selected={pane === id}
            aria-controls={id}
            onClick={() => show(id)}
          >
            <span className={`i ${icon}`} aria-hidden="true"></span>
            {label}
            {id === "problemy" && (
              <span className="count">{problems.length}</span>
            )}
            {id === "edytor" && !valid && (
              <>
                <span
                  className="i i-x-circle review-tab-error"
                  aria-hidden="true"
                ></span>
                <span className="visually-hidden">, JSON z błędami</span>
              </>
            )}
          </button>
        ))}
      </div>

      <div className="ws">
        <section {...paneProps("problemy")}>
          <ProblemList
            problems={problems}
            current={current}
            describe={describe}
            onSelect={(i) => go(i)}
          />
        </section>

        <section {...paneProps("edytor")}>
          <div className="pane__head">
            <h2 id="edytor-h">JSON</h2>
            <div className="end">
              <button
                className="btn btn--ghost btn--sm"
                type="button"
                disabled={Boolean(check.syntaxError)}
                onClick={() => editorRef.current?.format()}
              >
                Formatuj
              </button>
            </div>
          </div>
          <div className="pane__body">
            <JsonEditor
              ref={editorRef}
              initial={initial}
              onChange={setText}
              confidence={result.confidence.elements}
              diagnostics={diagnostics}
              describedBy="schema-state"
            />
          </div>
          <div className="pane__foot" id="schema-state" aria-live="polite">
            {check.syntaxError ? (
              <span className="schema schema--error">
                <span className="i i-x-circle" aria-hidden="true"></span>
                <span>
                  Błąd składni w{" "}
                  <button
                    type="button"
                    className="linklike"
                    onClick={() =>
                      check.syntaxError &&
                      editorRef.current?.goTo(check.syntaxError.from)
                    }
                  >
                    linii {check.syntaxError.line}
                  </button>
                  . Podgląd pokazuje ostatnią poprawną wersję.
                </span>
              </span>
            ) : check.schemaErrors.length ? (
              <>
                <span className="schema schema--error">
                  <span className="i i-x-circle" aria-hidden="true"></span>
                  {plural(check.schemaErrors.length, [
                    "niezgodność",
                    "niezgodności",
                    "niezgodności",
                  ])}{" "}
                  ze schematem
                </span>
                <ul className="schema-errors">
                  {check.schemaErrors.slice(0, 20).map((e, i) => (
                    <li key={i}>
                      <button
                        type="button"
                        className="linklike"
                        onClick={() => editorRef.current?.goTo(e.from)}
                      >
                        Linia {e.line}
                      </button>
                      : {e.message}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <span className="schema schema--ok">
                <span className="i i-check-circle" aria-hidden="true"></span>
                Zgodny ze schematem eUsługi
              </span>
            )}
          </div>
        </section>

        <div className="right-head">
          <div className="tabs" role="tablist" aria-label="Prawa kolumna">
            {(
              [
                ["podglad", "Podgląd formularza"],
                ["oryginal", "Oryginał"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                className="tab"
                role="tab"
                type="button"
                aria-selected={right === id}
                aria-controls={id}
                onClick={() => show(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="muted note">
            {right === "oryginal"
              ? (fileName ?? "wgrany dokument")
              : "tak zobaczy go wnioskodawca w eUsłudze"}
          </span>
        </div>

        <section {...paneProps("oryginal")}>
          <div className="pane__head">
            <h2 id="oryginal-h">Oryginał</h2>
            <span className="muted note">{fileName ?? "wgrany dokument"}</span>
          </div>
          <div className="pane__body">
            <SourceView jobId={jobId} sourceText={result.source_text} />
          </div>
        </section>

        <section {...paneProps("podglad")}>
          <div className="pane__head">
            <h2 id="podglad-h">Podgląd formularza</h2>
            <span className="muted note">
              tak zobaczy go wnioskodawca w eUsłudze
            </span>
          </div>
          <div className="pane__body">
            {!valid && (
              <div className="alert alert--info review-alert" role="status">
                <span className="i i-info" aria-hidden="true"></span>
                <p>
                  Podgląd sprzed ostatniej zmiany: JSON{" "}
                  {check.syntaxError
                    ? "ma błąd składni"
                    : "nie przechodzi schematu"}
                  .
                </p>
              </div>
            )}
            <PreviewBoundary form={form}>
              <FormPreview
                form={form}
                confidence={result.confidence.elements}
                selection={selection}
              />
            </PreviewBoundary>
          </div>
        </section>
      </div>
    </main>
  );
}
