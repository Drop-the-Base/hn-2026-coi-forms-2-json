import type { ReactNode } from "react";
import {
  confidenceLevel,
  ConfidenceBadge,
  REVIEW_THRESHOLD,
} from "../../shared/confidence";
import {
  htmlToText,
  isRequired,
  PROFILE_VALUE,
  type Answer,
  type Answers,
  type FieldStatus,
  type FormField,
  type Question,
} from "./form";

interface Props {
  /** JSON path of `questions`, e.g. "tabs[1].questions"; confidence and selection use these paths. */
  path: string;
  confidence: Record<string, number>;
  current?: string;
  questions: Question[];
  answers: Answers;
  statuses: Record<string, FieldStatus> | null;
  onAnswer: (fieldId: string, value: Answer) => void;
}

// Renders questions on the 3-column eUsługa grid; sections recurse into their own grid.
export function PreviewQuestions(props: Props) {
  const sorted = [...props.questions].sort((a, b) => a.y - b.y || a.x - b.x);
  return (
    <div className="eu-grid">
      {sorted.map((q) => {
        const status = props.statuses?.[q.field.id];
        // Until the first evaluation, conditional fields stay hidden like on a fresh form.
        const shown = status
          ? status.show
          : !q.field.states?.some((s) => s.type === "SHOW");
        if (!shown) return null;
        const path = `${props.path}[${props.questions.indexOf(q)}].field`;
        const value = props.confidence[path];
        const flagged = value !== undefined && value < REVIEW_THRESHOLD;
        return (
          <div
            key={q.field.id}
            className={
              path === props.current ? "eu-cell is-current" : "eu-cell"
            }
            style={{ gridColumn: `${q.x + 1} / span ${q.cols}` }}
          >
            {flagged && (
              <span
                className={`mark mark--${confidenceLevel(value)} eu-mark`}
                aria-hidden="true"
              ></span>
            )}
            <PreviewField
              {...props}
              path={path}
              badge={flagged && <ConfidenceBadge value={value} />}
              field={q.field}
              readOnly={Boolean(q.field.readOnly || status?.readOnly)}
              failedQuery={status?.failedQuery}
            />
          </div>
        );
      })}
    </div>
  );
}

function PreviewField({
  path,
  confidence,
  current,
  badge,
  field,
  readOnly,
  failedQuery,
  answers,
  statuses,
  onAnswer,
}: Props & {
  badge: ReactNode;
  field: FormField;
  readOnly: boolean;
  failedQuery?: string;
}) {
  const id = `eu-${field.id}`;
  const hintId = `${id}-hint`;
  const hint = htmlToText(field.description);
  const required = isRequired(field);
  const answer = answers[field.id];
  const text = typeof answer === "string" ? answer : "";
  const prefill =
    typeof field.defaultValue === "string" &&
    PROFILE_VALUE.test(field.defaultValue)
      ? `Z profilu: ${field.defaultValue}`
      : undefined;
  const control = {
    id,
    required,
    readOnly,
    "aria-describedby": hint ? hintId : undefined,
  };

  const label = (
    <label className="eu-label" htmlFor={id}>
      {field.title}
      {required && " (wymagane)"} {badge}
    </label>
  );
  const hintText = hint && (
    <p className="eu-hint" id={hintId}>
      {hint}
    </p>
  );
  const warning = failedQuery && (
    <p className="eu-warning" role="note">
      Nie udało się obliczyć warunku: <code>{failedQuery}</code>
    </p>
  );

  switch (field.type) {
    case "SECTION":
    case "REPEATING_SECTION":
      return (
        <section className="eu-card" aria-labelledby={`${id}-h`}>
          <h4 id={`${id}-h`}>
            {field.title} {badge}
          </h4>
          {hint && <p className="eu-hint">{hint}</p>}
          {warning}
          <PreviewQuestions
            path={`${path}.repeatingSectionGrid`}
            confidence={confidence}
            current={current}
            questions={field.repeatingSectionGrid ?? []}
            answers={answers}
            statuses={statuses}
            onAnswer={onAnswer}
          />
        </section>
      );
    case "TEXT_FIELD":
    case "NUMBER":
    case "DATEPICKER":
      return (
        <div className="eu-q">
          {label}
          {hintText}
          <input
            {...control}
            className="eu-input"
            type={
              field.type === "NUMBER"
                ? "number"
                : field.type === "DATEPICKER"
                  ? "date"
                  : "text"
            }
            value={text}
            placeholder={prefill}
            onChange={(e) => onAnswer(field.id, e.target.value)}
          />
          {warning}
        </div>
      );
    case "TEXTAREA":
      return (
        <div className="eu-q">
          {label}
          {hintText}
          <textarea
            {...control}
            className="eu-input eu-textarea"
            value={text}
            onChange={(e) => onAnswer(field.id, e.target.value)}
          />
          {warning}
        </div>
      );
    case "SELECT": {
      const values = Array.isArray(answer) ? answer : answer ? [answer] : [];
      // Dictionary-backed selects carry no options in the JSON; show the default so SHOW conditions work.
      const options = field.options?.length
        ? field.options
        : values.map((v) => ({ id: v, name: v }));
      return (
        <div className="eu-q">
          {label}
          {hintText}
          <select
            {...control}
            className="eu-input"
            disabled={readOnly}
            value={values[0] ?? ""}
            onChange={(e) =>
              onAnswer(field.id, e.target.value ? [e.target.value] : [])
            }
          >
            <option value="">Wybierz</option>
            {options.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
          {field.dictionaryName && (
            <p className="eu-hint">Słownik: {field.dictionaryName}</p>
          )}
          {warning}
        </div>
      );
    }
    case "RADIO":
    case "CHECKBOX": {
      const multiple = field.type === "CHECKBOX";
      const values = Array.isArray(answer) ? answer : answer ? [answer] : [];
      if (multiple && !field.options?.length)
        return (
          <div className="eu-q">
            <label className="eu-choice">
              <input
                {...control}
                type="checkbox"
                disabled={readOnly}
                checked={values.length > 0}
                onChange={(e) =>
                  onAnswer(field.id, e.target.checked ? ["true"] : [])
                }
              />
              {field.title}
              {required && " (wymagane)"} {badge}
            </label>
            {hintText}
            {warning}
          </div>
        );
      return (
        <fieldset
          className="eu-q eu-fieldset"
          aria-describedby={hint ? hintId : undefined}
        >
          <legend className="eu-label">
            {field.title}
            {required && " (wymagane)"} {badge}
          </legend>
          {hintText}
          {field.options?.map((o) => (
            <label key={o.id} className="eu-choice">
              <input
                type={multiple ? "checkbox" : "radio"}
                name={id}
                value={o.id}
                required={required && !multiple}
                disabled={readOnly}
                checked={values.includes(o.id)}
                onChange={(e) =>
                  onAnswer(
                    field.id,
                    !multiple
                      ? o.id
                      : e.target.checked
                        ? [...values, o.id]
                        : values.filter((v) => v !== o.id),
                  )
                }
              />
              {o.name}
            </label>
          ))}
          {warning}
        </fieldset>
      );
    }
    case "FILE_UPLOADER":
      return (
        <div className="eu-q">
          {label}
          {hintText}
          <div className="eu-file">
            <input {...control} type="file" disabled={readOnly} />
          </div>
          {warning}
        </div>
      );
    case "TEXT_BLOCK":
    case "INFO_SECTION":
      return (
        <div className={field.type === "INFO_SECTION" ? "eu-info" : undefined}>
          {(field.title || badge) && (
            <p className="eu-label">
              {field.title} {badge}
            </p>
          )}
          <p className="eu-text">{hint}</p>
          {warning}
        </div>
      );
    case "CONSENT_SECTION":
      return (
        <div className="eu-q">
          {badge}
          {field.consentSectionConfig?.consents?.map((c, i) => (
            <label key={i} className="eu-choice">
              <input type="checkbox" required={c.required} />
              <span>
                {htmlToText(c.description)}
                {c.required && " (wymagane)"}
              </span>
            </label>
          ))}
          {warning}
        </div>
      );
    default:
      return (
        <p className="eu-unknown">
          Nieobsługiwany typ pola: {field.type} {badge}
        </p>
      );
  }
}
