import {
  useEffect,
  useEffectEvent,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { Link } from "react-router";
import { elementPath, FormPreview, type FormJson } from "../form-preview";
import {
  ConfidenceBadge,
  confidenceLevel,
  formatConfidence,
} from "../../shared/confidence";
import { FieldInspector } from "./FieldInspector";
import { FormTree } from "./FormTree";
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
  fixSchemaTypo,
  getAt,
  setAt,
  type ReviewResult,
} from "./review";
import "./ReviewScreen.css";

// Wide screen: list | column A | column B, the clerk picks the view in each work column, so any pair sits side by side.
// Narrow screen: column A only, with "lista" as one more view.
type View = "pole" | "edytor" | "oryginal" | "podglad";
type Left = "struktura" | "problemy";
const VIEWS: [View, string][] = [
  ["pole", "Pole"],
  ["edytor", "JSON"],
  ["oryginal", "Oryginał"],
  ["podglad", "Podgląd"],
];
const narrow = () => window.matchMedia?.("(max-width: 64rem)").matches ?? false;

const LEVEL_WORD = { low: "niska", medium: "średnia", high: "wysoka" };

interface Props {
  result: ReviewResult;
  /** eUsługi form JSON Schema as served by GET /api/v1/form-schema. */
  schema: unknown;
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
function ReviewScreen({ result, schema, jobId, fileName }: Props) {
  const formSchema = useMemo(() => fixSchemaTypo(schema), [schema]);
  const initial = useMemo(
    () => JSON.stringify(result.form, null, 2),
    [result.form],
  );
  const problems = useMemo(() => buildProblems(result), [result]);
  const editorRef = useRef<JsonEditorHandle>(null);
  const [text, setText] = useState(initial);
  const check = useMemo(() => checkJson(text, formSchema), [text, formSchema]);
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

  // The preview keeps the last JSON that passed the schema (ekran-przegladu.md §7).
  const [form, setForm] = useState<FormJson>(result.form);
  if (valid && check.data !== form) setForm(check.data as FormJson);

  const [current, setCurrent] = useState<number | null>(null);
  const [selection, setSelection] = useState<{ path: string } | null>(null);
  // The element open in the inspector; null is the form itself.
  const [selected, setSelected] = useState<string | null>(null);
  const [a, setA] = useState<View | "lista">("pole");
  const [b, setB] = useState<View>("podglad");
  const [left, setLeft] = useState<Left>(
    problems.length ? "problemy" : "struktura",
  );
  // Back on a wide screen after "lista" was picked on a narrow one: column A shows an editing view.
  const aView: View = a === "lista" ? (b === "pole" ? "edytor" : "pole") : a;
  /** Picking a view the other column shows swaps the two columns. */
  function choose(column: "a" | "b", view: View | "lista") {
    if (column === "a") {
      if (view === b) setB(aView);
      setA(view);
    } else if (view !== "lista") {
      if (view === aView) setA(b);
      setB(view);
    }
  }
  const shows = (view: View) => a === view || (!narrow() && b === view);
  const flagged = useMemo(() => {
    const map = new Map<string, "error" | "check">();
    for (const p of problems) {
      const at = elementPath(p.path);
      if (map.get(at) !== "error") map.set(at, p.kind);
    }
    return map;
  }, [problems]);

  /** Opens an element in the inspector and the preview; in the JSON tab it also jumps there. */
  function pick(path: string) {
    setSelected(path === "title" ? null : elementPath(path));
    setSelection({ path });
    if (shows("edytor"))
      requestAnimationFrame(() => editorRef.current?.reveal(path));
  }

  /** An inspector change goes into the JSON text, so the editor, checks and preview follow it. */
  function edit(path: string, value: unknown) {
    const next = JSON.stringify(
      setAt(check.data ?? form, path, value),
      null,
      2,
    );
    setText(next);
    editorRef.current?.replace(next);
  }

  const [announcement, setAnnouncement] = useState("");
  const describe = (path: string) => describePath(form, path);

  function go(index: number, wrapped = false) {
    const problem = problems[index];
    setCurrent(index);
    pick(problem.path);
    if (!shows("pole") && !shows("edytor")) choose("a", "pole");
    requestAnimationFrame(() => {
      const found = getAt(check.data, elementPath(problem.path)) !== undefined;
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
  /** Where a view sits: column A or B on a wide screen; on a narrow one only column A is shown. */
  const placed = (view: View) => {
    const column = aView === view ? "a" : b === view ? "b" : undefined;
    return {
      "data-col": column,
      "data-a": a === view || undefined,
      "data-off": column ? undefined : true,
    };
  };
  const goToLine = (from: number) => {
    if (!shows("edytor")) choose("a", "edytor");
    requestAnimationFrame(() => editorRef.current?.goTo(from));
  };

  return (
    <main className="review">
      <a className="skip" href="#kolumna-a">
        Przejdź do edycji
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

      <div className="ws">
        <section
          id="lista"
          className="pane"
          aria-label="Struktura i problemy"
          data-a={a === "lista" || undefined}
        >
          <div className="pane__head pane__head--tabs">
            <div
              className="tabs"
              role="tablist"
              aria-label="Lista"
              onKeyDown={tabArrows}
            >
              <button
                className="tab"
                role="tab"
                type="button"
                aria-selected={left === "struktura"}
                tabIndex={left === "struktura" ? 0 : -1}
                aria-controls="struktura"
                onClick={() => setLeft("struktura")}
              >
                Struktura
              </button>
              <button
                className="tab"
                role="tab"
                type="button"
                aria-selected={left === "problemy"}
                tabIndex={left === "problemy" ? 0 : -1}
                aria-controls="problemy"
                onClick={() => setLeft("problemy")}
              >
                Problemy <span className="count">{problems.length}</span>
              </button>
            </div>
          </div>
          <div
            id="struktura"
            className="pane__body"
            role="tabpanel"
            aria-label="Struktura"
            data-off={left !== "struktura" || undefined}
          >
            <FormTree
              form={form}
              selected={selected}
              flagged={flagged}
              confidence={result.confidence.elements}
              onSelect={(path) => {
                pick(path);
                if (narrow()) choose("a", "pole");
              }}
            />
          </div>
          <div
            id="problemy"
            className="subpane"
            role="tabpanel"
            aria-label="Problemy"
            data-off={left !== "problemy" || undefined}
          >
            <ProblemList
              problems={problems}
              current={current}
              describe={describe}
              onSelect={(i) => go(i)}
            />
          </div>
        </section>

        {(["a", "b"] as const).map((column) => {
          const view = column === "a" ? aView : b;
          return (
            <div
              key={column}
              id={`kolumna-${column}`}
              className={`colhead colhead--${column}`}
            >
              <div
                className="tabs"
                role="tablist"
                aria-label={column === "a" ? "Edycja" : "Druga kolumna"}
                onKeyDown={tabArrows}
              >
                {[
                  ...VIEWS,
                  ...(column === "a" ? [["lista", "Lista"] as const] : []),
                ].map(([id, label]) => {
                  const on = (column === "a" ? a : b) === id;
                  return (
                    <button
                      key={id}
                      className={id === "lista" ? "tab tab--narrow" : "tab"}
                      role="tab"
                      type="button"
                      aria-selected={on}
                      tabIndex={on ? 0 : -1}
                      aria-controls={id}
                      onClick={() => choose(column, id)}
                    >
                      {label}
                      {id === "edytor" && !valid && <JsonErrorMark />}
                      {id === "lista" && (
                        <span className="count">{problems.length}</span>
                      )}
                    </button>
                  );
                })}
              </div>
              <div className="end">
                {view === "edytor" && (
                  <button
                    className="btn btn--ghost btn--sm"
                    type="button"
                    disabled={Boolean(check.syntaxError)}
                    onClick={() => editorRef.current?.format()}
                  >
                    Formatuj
                  </button>
                )}
                {view === "oryginal" && (
                  <span className="muted note">
                    {fileName ?? "wgrany dokument"}
                  </span>
                )}
                {view === "podglad" && (
                  <>
                    <span className="muted note">
                      tak zobaczy go wnioskodawca
                    </span>
                    {/* Print styles leave only the preview, all pages expanded (FR-E6). */}
                    <button
                      className="btn btn--ghost btn--sm"
                      type="button"
                      onClick={() => window.print()}
                    >
                      Drukuj / zapisz PDF
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}

        <section
          id="pole"
          className="pane__body pane--view"
          aria-label="Pole"
          {...placed("pole")}
        >
          <FieldInspector
            form={(check.data ?? form) as FormJson}
            path={selected}
            confidence={result.confidence.elements}
            focus={
              problem && selected && problem.path.startsWith(`${selected}.`)
                ? problem.path.slice(selected.length + 1).split(/[.[]/)[0]
                : undefined
            }
            editable={!check.syntaxError}
            onEdit={edit}
            describe={describe}
          />
        </section>
        <section
          id="edytor"
          className="pane__body pane--view"
          aria-label="JSON"
          {...placed("edytor")}
        >
          <JsonEditor
            ref={editorRef}
            initial={initial}
            onChange={setText}
            confidence={result.confidence.elements}
            diagnostics={diagnostics}
            describedBy="schema-state"
          />
        </section>
        <section
          id="oryginal"
          className="pane__body pane--view"
          aria-label="Oryginał"
          {...placed("oryginal")}
        >
          <SourceView jobId={jobId} sourceText={result.source_text} />
        </section>
        <section
          id="podglad"
          className="pane__body pane--view pane--preview"
          aria-label="Podgląd formularza"
          {...placed("podglad")}
        >
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
              onSelect={pick}
            />
          </PreviewBoundary>
        </section>

        <div className="ws__foot" id="schema-state" aria-live="polite">
          {check.syntaxError ? (
            <span className="schema schema--error">
              <span className="i i-x-circle" aria-hidden="true"></span>
              <span>
                Błąd składni w{" "}
                <button
                  type="button"
                  className="linklike"
                  onClick={() =>
                    check.syntaxError && goToLine(check.syntaxError.from)
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
                      onClick={() => goToLine(e.from)}
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
      </div>
    </main>
  );
}

function JsonErrorMark() {
  return (
    <>
      <span className="i i-x-circle review-tab-error" aria-hidden="true"></span>
      <span className="visually-hidden">, JSON z błędami</span>
    </>
  );
}

/** Arrow keys move between tabs of a tablist and open the tab (WAI-ARIA tabs pattern, NFR-15). */
function tabArrows(e: ReactKeyboardEvent<HTMLDivElement>) {
  const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
  if (!step) return;
  // Tabs hidden by the layout (the narrow-only "Lista") are skipped.
  const tabs = [
    ...e.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]'),
  ].filter((t) => getComputedStyle(t).display !== "none");
  const next =
    tabs[
      (tabs.indexOf(e.target as HTMLButtonElement) + step + tabs.length) %
        tabs.length
    ];
  next.focus();
  next.click();
}
