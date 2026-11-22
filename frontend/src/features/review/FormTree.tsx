import { confidenceLevel, REVIEW_THRESHOLD } from "../../shared/confidence";
import { htmlToText, type FormJson, type Question } from "../form-preview";
import { fieldTypeLabel } from "./review";

interface Props {
  form: FormJson;
  selected: string | null;
  /** Element path → the worst problem on it; the tree shows it next to the node. */
  flagged: Map<string, "error" | "check">;
  confidence: Record<string, number>;
  onSelect: (path: string) => void;
}

/** Pages, sections and fields of the form as a list a clerk can scan (ekran-przegladu.md, układ z drzewem). */
export function FormTree({
  form,
  selected,
  flagged,
  confidence,
  onSelect,
}: Props) {
  const node = (path: string, kind: string, title: string) => {
    const problem = flagged.get(path);
    const value = confidence[path];
    return (
      <button
        type="button"
        className="tree__node"
        aria-current={path === selected ? "true" : undefined}
        onClick={() => onSelect(path)}
      >
        {value !== undefined && value < REVIEW_THRESHOLD ? (
          <span
            className={`mark mark--${confidenceLevel(value)} tree__mark`}
            aria-hidden="true"
          ></span>
        ) : (
          <span className="tree__mark" aria-hidden="true"></span>
        )}
        <span className="tree__text">
          <span className="tree__title" title={title || undefined}>
            {title || "(bez tytułu)"}
          </span>
          <span className="tree__kind">{kind}</span>
        </span>
        {problem && (
          <span
            className={`i ${problem === "error" ? "i-x-circle tree__err" : "i-alert tree__check"}`}
            aria-hidden="true"
          ></span>
        )}
        {problem && (
          <span className="visually-hidden">
            {problem === "error" ? ", błąd" : ", do sprawdzenia"}
          </span>
        )}
      </button>
    );
  };

  const questions = (path: string, list: Question[]) => (
    <ol className="tree__list">
      {[...list]
        .sort((a, b) => a.y - b.y || a.x - b.x)
        .map((q) => {
          const fieldPath = `${path}[${list.indexOf(q)}].field`;
          const children = q.field.repeatingSectionGrid ?? [];
          return (
            <li key={q.field.id || fieldPath}>
              {node(
                fieldPath,
                fieldTypeLabel(q.field.type),
                q.field.title || htmlToText(q.field.description).slice(0, 60),
              )}
              {children.length > 0 &&
                questions(`${fieldPath}.repeatingSectionGrid`, children)}
            </li>
          );
        })}
    </ol>
  );

  return (
    <nav className="tree" aria-label="Struktura formularza">
      <ol className="tree__list tree__list--pages">
        {form.tabs.map((tab, i) => (
          <li key={tab.id || i}>
            {node(`tabs[${i}]`, `Strona ${i + 1}`, tab.title)}
            {questions(`tabs[${i}].questions`, tab.questions ?? [])}
          </li>
        ))}
      </ol>
    </nav>
  );
}
