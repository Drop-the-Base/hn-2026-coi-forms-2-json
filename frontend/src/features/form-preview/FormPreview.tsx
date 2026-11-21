import { useEffect, useRef, useState } from "react";
import {
  elementPath,
  evaluateStates,
  initialAnswers,
  pageOrder,
  type Answer,
  type FieldStatus,
  type FormJson,
} from "./form";
import { PreviewQuestions } from "./PreviewQuestions";
import "./FormPreview.css";

interface Props {
  form: FormJson;
  /** Confidence per JSON path (FR-T1); elements below the threshold get a margin mark and a badge. */
  confidence?: Record<string, number>;
  /** A new object moves the preview to the page of `path` and marks its element. */
  selection?: { path: string } | null;
}

// Interactive render of an eUsługa form JSON (FR-E5). Answers stay local; give a new `key` for a new form.
export function FormPreview({ form, confidence = {}, selection }: Props) {
  const { tabs, consistent } = pageOrder(form);
  const [page, setPage] = useState(0);
  const [shownSelection, setShownSelection] = useState(selection);
  if (selection !== shownSelection) {
    setShownSelection(selection);
    const tabIndex = Number(selection?.path.match(/^tabs\[(\d+)\]/)?.[1]);
    const index = tabs.indexOf(form.tabs[tabIndex]);
    if (index >= 0) setPage(index);
  }
  const rootRef = useRef<HTMLDivElement>(null);
  const [answers, setAnswers] = useState(() => initialAnswers(form));
  const [statuses, setStatuses] = useState<Record<string, FieldStatus> | null>(
    null,
  );
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    let current = true;
    evaluateStates(form, answers).then((s) => current && setStatuses(s));
    return () => {
      current = false;
    };
  }, [form, answers]);

  useEffect(() => {
    // scrollIntoView is missing in jsdom; "nearest" without smooth stays instant for reduced motion.
    rootRef.current
      ?.querySelector(".is-current")
      ?.scrollIntoView?.({ block: "nearest" });
  }, [selection, page]);

  const tab = tabs[page];
  const goTo = (index: number) => {
    setPage(index);
    // Move focus to the new page so keyboard and screen reader users land on it.
    requestAnimationFrame(() => titleRef.current?.focus());
  };
  const answer = (fieldId: string, value: Answer) =>
    setAnswers((a) => ({ ...a, [fieldId]: value }));

  return (
    <div className="eu" ref={rootRef}>
      <h2 className="eu-form-title">{form.title}</h2>
      {!consistent && (
        <p className="eu-alert" role="status">
          Przepływ stron jest niespójny. Strony pokazano w kolejności z pliku.
        </p>
      )}
      <ol className="eu-steps" aria-label="Strony formularza">
        {tabs.map((t, i) => (
          <li key={t.id}>
            <button
              type="button"
              aria-current={i === page ? "step" : undefined}
              aria-label={`Strona ${i + 1}, ${t.title}`}
              onClick={() => goTo(i)}
            >
              <span className="eu-step-n">{i + 1}</span>
              {t.title}
            </button>
          </li>
        ))}
      </ol>
      {tab && (
        <>
          <h3 className="eu-page-title" ref={titleRef} tabIndex={-1}>
            {tab.title}
          </h3>
          <PreviewQuestions
            path={`tabs[${form.tabs.indexOf(tab)}].questions`}
            confidence={confidence}
            current={selection ? elementPath(selection.path) : undefined}
            questions={tab.questions}
            answers={answers}
            statuses={statuses}
            onAnswer={answer}
          />
        </>
      )}
      <div className="eu-foot">
        {page > 0 && (
          <button
            type="button"
            className="eu-back"
            onClick={() => goTo(page - 1)}
          >
            Wróć
          </button>
        )}
        {page < tabs.length - 1 && (
          <button
            type="button"
            className="eu-next"
            onClick={() => goTo(page + 1)}
          >
            Dalej
          </button>
        )}
      </div>
    </div>
  );
}
