import { useEffect, useRef, type ReactNode } from "react";
import { ConfidenceBadge, REVIEW_THRESHOLD } from "../../shared/confidence";
import type { FormField, FormJson } from "../form-preview";
import { FIELD_TYPES, fieldTypeLabel, getAt } from "./review";

// Validators from the reference forms (K-05: REQUIRED is the "required" switch, the rest are format checks).
const VALIDATORS: Record<string, string> = {
  EMAIL: "Adres e-mail",
  PESEL: "PESEL",
  NIP: "NIP",
  REGON: "REGON",
  ZIP_CODE: "Kod pocztowy",
};
const WITH_OPTIONS = new Set(["SELECT", "RADIO", "CHECKBOX"]);
const NO_INPUT = new Set([
  "SECTION",
  "REPEATING_SECTION",
  "TEXT_BLOCK",
  "CONSENT_SECTION",
]);
const STATE_WORD: Record<string, string> = {
  SHOW: "Pokaż, gdy",
  READ_ONLY: "Tylko do odczytu, gdy",
};

/** "Pełnomocnik prawny" → "pelnomocnik_prawny", like the techNames in the reference forms. */
export const techName = (text: string) =>
  text
    .replace(/ł/g, "l")
    .replace(/Ł/g, "L")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^A-Za-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();

interface Props {
  form: FormJson;
  /** Path of the selected tab ("tabs[1]") or field ("tabs[1].questions[0].field"); null for the whole form. */
  path: string | null;
  confidence: Record<string, number>;
  /** Part of the element the current problem is about ("options", "validation"…); the inspector scrolls to it. */
  focus?: string;
  /** False while the JSON has a syntax error: nothing to edit until it parses. */
  editable: boolean;
  onEdit: (path: string, value: unknown) => void;
  describe: (path: string) => string;
}

/** Edits the selected element with form controls instead of JSON (FR-T2). */
export function FieldInspector({
  form,
  path,
  confidence,
  focus,
  editable,
  onEdit,
  describe,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    rootRef.current
      ?.querySelector(`[data-group="${focus ?? "title"}"]`)
      ?.scrollIntoView?.({ block: "nearest" });
  }, [path, focus]);
  if (!editable)
    return (
      <p className="inspector__empty">
        JSON ma błąd składni. Popraw go w zakładce JSON, potem wróć tutaj.
      </p>
    );

  const text = (label: string, at: string, value: string, hint?: string) => (
    <Field label={label} id={`f-${at}`} hint={hint}>
      <input
        className="input"
        id={`f-${at}`}
        value={value}
        onChange={(e) => onEdit(at, e.target.value)}
      />
    </Field>
  );

  if (path === null || !path.includes(".field")) {
    const tab = path === null ? null : (getAt(form, path) as { title: string });
    return (
      <div className="inspector">
        <p className="inspector__kind">
          {tab ? `Strona ${Number(path?.match(/\d+/)?.[0]) + 1}` : "Formularz"}
        </p>
        {tab
          ? text("Tytuł strony", `${path}.title`, tab.title ?? "")
          : text("Tytuł formularza", "title", form.title ?? "")}
        <p className="muted inspector__hint">
          Wybierz problem (F8) albo pole w strukturze lub w podglądzie. Tutaj je
          poprawisz, a zmianę od razu zobaczysz w podglądzie.
        </p>
      </div>
    );
  }

  const field = getAt(form, path) as FormField | undefined;
  if (!field)
    return (
      <p className="inspector__empty">
        Tego elementu nie ma już w JSON-ie. Wybierz inny w strukturze.
      </p>
    );

  const set = (key: string, value: unknown) => onEdit(`${path}.${key}`, value);
  const validation = Array.isArray(field.validation) ? field.validation : [];
  const toggle = (name: string, on: boolean) =>
    set(
      "validation",
      on ? [...validation, name] : validation.filter((v) => v !== name),
    );
  const options = field.options ?? [];
  const setOption = (i: number, name: string) =>
    set(
      "options",
      options.map((o, j) =>
        j === i ? { ...o, name, techName: techName(name) } : o,
      ),
    );
  const value = confidence[path];
  const raw = field as unknown as Record<string, unknown>;

  return (
    <div className="inspector" ref={rootRef}>
      <div className="inspector__head" data-group="title">
        <p className="inspector__kind">{fieldTypeLabel(field.type)}</p>
        {value !== undefined && value < REVIEW_THRESHOLD && (
          <ConfidenceBadge value={value} />
        )}
      </div>
      <p className="muted inspector__where">{describe(path)}</p>

      {text("Tytuł", `${path}.title`, field.title ?? "")}

      <Field label="Rodzaj pola" id="f-type">
        <select
          className="input"
          id="f-type"
          value={field.type}
          onChange={(e) => set("type", e.target.value)}
        >
          {!(field.type in FIELD_TYPES) && (
            <option value={field.type}>{field.type}</option>
          )}
          {Object.entries(FIELD_TYPES).map(([type, label]) => (
            <option key={type} value={type}>
              {label}
            </option>
          ))}
        </select>
      </Field>

      {!NO_INPUT.has(field.type) && (
        <fieldset className="inspector__group" data-group="validation">
          <legend>Reguły</legend>
          <Check
            label="Wymagane"
            checked={validation.includes("REQUIRED")}
            onChange={(on) => toggle("REQUIRED", on)}
          />
          <Check
            label="Tylko do odczytu"
            checked={Boolean(field.readOnly)}
            onChange={(on) => set("readOnly", on)}
          />
        </fieldset>
      )}

      {!NO_INPUT.has(field.type) && !WITH_OPTIONS.has(field.type) && (
        <fieldset className="inspector__group inspector__group--grid">
          <legend>Format odpowiedzi</legend>
          {Object.entries(VALIDATORS).map(([name, label]) => (
            <Check
              key={name}
              label={label}
              checked={validation.includes(name)}
              onChange={(on) => toggle(name, on)}
            />
          ))}
          {validation
            .filter((v) => v !== "REQUIRED" && !(v in VALIDATORS))
            .map((v) => (
              <Check
                key={v}
                label={v}
                checked
                onChange={(on) => toggle(v, on)}
              />
            ))}
        </fieldset>
      )}

      {(WITH_OPTIONS.has(field.type) || options.length > 0) && (
        <fieldset className="inspector__group" data-group="options">
          <legend>Opcje do wyboru</legend>
          {field.dictionaryName != null &&
            text(
              "Słownik",
              `${path}.dictionaryName`,
              field.dictionaryName,
              "Opcje przychodzą ze słownika eUsługi.",
            )}
          <ol className="inspector__options">
            {options.map((option, i) => (
              <li key={option.id || i} className="input-row">
                <label className="visually-hidden" htmlFor={`f-opt-${i}`}>
                  Opcja {i + 1}
                </label>
                <input
                  className="input"
                  id={`f-opt-${i}`}
                  value={option.name}
                  onChange={(e) => setOption(i, e.target.value)}
                />
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  aria-label={`Usuń opcję ${option.name || i + 1}`}
                  onClick={() =>
                    set(
                      "options",
                      options.filter((_, j) => j !== i),
                    )
                  }
                >
                  <span className="i i-trash" aria-hidden="true"></span>
                </button>
              </li>
            ))}
          </ol>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() =>
              set("options", [
                ...options,
                { id: crypto.randomUUID(), name: "", techName: "" },
              ])
            }
          >
            Dodaj opcję
          </button>
        </fieldset>
      )}

      {!NO_INPUT.has(field.type) &&
        text(
          "Podpowiedź",
          `${path}.tooltipMessage`,
          String(raw.tooltipMessage ?? ""),
        )}

      <Field
        label={/<[a-z]/i.test(field.description ?? "") ? "Opis (HTML)" : "Opis"}
        id="f-description"
      >
        <textarea
          className="input input--mono inspector__area"
          id="f-description"
          rows={3}
          value={field.description ?? ""}
          onChange={(e) => set("description", e.target.value)}
        />
      </Field>

      {(field.states ?? []).length > 0 && (
        <fieldset className="inspector__group" data-group="states">
          <legend>Warunki</legend>
          {(field.states ?? []).map((state, i) => (
            <div key={i}>
              {text(
                STATE_WORD[state.type] ?? state.type,
                `${path}.states[${i}].query`,
                state.query,
              )}
            </div>
          ))}
        </fieldset>
      )}

      <details className="inspector__more">
        <summary>Szczegóły techniczne</summary>
        {text(
          "Nazwa techniczna",
          `${path}.techName`,
          String(raw.techName ?? ""),
          "Klucz pola w danych wniosku.",
        )}
        <p className="muted inspector__id">
          id <span className="mono">{field.id}</span>
        </p>
      </details>
    </div>
  );
}

function Field(props: {
  label: string;
  id: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={props.id}>
        {props.label}
      </label>
      {props.children}
      {props.hint && <p className="field__hint">{props.hint}</p>}
    </div>
  );
}

function Check(props: {
  label: string;
  checked: boolean;
  onChange: (on: boolean) => void;
}) {
  return (
    <label className="inspector__check">
      <input
        type="checkbox"
        checked={props.checked}
        onChange={(e) => props.onChange(e.target.checked)}
      />
      {props.label}
    </label>
  );
}
