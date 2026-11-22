import jsonata from "jsonata";

// Shape of the eUsługa form JSON, as in the reference files (data/, wzorce 1 i 5).
export interface FormOption {
  id: string;
  name: string;
}

export interface FieldState {
  type: string;
  query: string;
}

export interface FormField {
  id: string;
  type: string;
  title: string;
  description?: string | null;
  options?: FormOption[];
  // Reference files sometimes hold {} instead of [] (K-05).
  validation?: string[] | Record<string, never>;
  readOnly?: boolean;
  repeatingSectionGrid?: Question[];
  states?: FieldState[] | null;
  defaultValue?: string | string[] | null;
  dictionaryName?: string | null;
  consentSectionConfig?: {
    consents?: { description: string; required?: boolean }[];
  } | null;
}

export interface Question {
  x: number;
  y: number;
  rows: number;
  cols: number;
  field: FormField;
}

export interface FormTab {
  id: string;
  title: string;
  type: string;
  questions: Question[];
}

export interface FormJson {
  title: string;
  tabs: FormTab[];
  flow: { links: { id: string; source: string; target: string }[] };
}

export type Answer = string | string[];
export type Answers = Record<string, Answer>;

export interface FieldStatus {
  show: boolean;
  readOnly: boolean;
  failedQuery?: string;
}

// Profile prefill such as "MLPZ.surname": eUsługa fills it from the user's data.
export const PROFILE_VALUE = /^[A-Z]+\.[A-Za-z]+$/;

export function allFields(questions: Question[]): FormField[] {
  return questions.flatMap((q) => [
    q.field,
    ...allFields(q.field.repeatingSectionGrid ?? []),
  ]);
}

// "tabs[1].questions[0].field.validation" → "tabs[1].questions[0].field": the deepest field the path points into.
export const elementPath = (path: string) =>
  path.match(/^.*\.field(?=\.|$)/)?.[0] ?? path;

/** Title of the field on `path` (or of a section around it) that a condition hides now; null when it is shown. */
export function hiddenBy(
  form: FormJson,
  path: string,
  statuses: Record<string, FieldStatus> | null,
): string | null {
  const segments = path.match(/[^.[\]]+/g) ?? [];
  let node: unknown = form;
  for (const segment of segments) {
    node = (node as Record<string, unknown> | null | undefined)?.[segment];
    if (segment !== "field" || !node) continue;
    const field = node as FormField;
    const status = statuses?.[field.id];
    const shown = status
      ? status.show
      : !field.states?.some((s) => s.type === "SHOW");
    if (!shown) return field.title || "bez tytułu";
  }
  return null;
}

export function isRequired(field: FormField): boolean {
  return (
    Array.isArray(field.validation) && field.validation.includes("REQUIRED")
  );
}

export function initialAnswers(form: FormJson): Answers {
  const answers: Answers = {};
  for (const field of form.tabs.flatMap((t) => allFields(t.questions))) {
    const value = field.defaultValue;
    if (
      Array.isArray(value) ? value.length : value && !PROFILE_VALUE.test(value)
    )
      answers[field.id] = value as Answer;
  }
  return answers;
}

// Pages in flow.links order; falls back to tabs[] order when the flow is not one chain over all tabs.
// shortcut: branching flows (one source, many targets) show only the first chain, upgrade with a branching generator.
export function pageOrder(form: FormJson): {
  tabs: FormTab[];
  consistent: boolean;
} {
  const byId = new Map(form.tabs.map((t) => [t.id, t]));
  const next = new Map(form.flow.links.map((l) => [l.source, l.target]));
  const targets = new Set(next.values());
  const ordered: FormTab[] = [];
  let tab = form.tabs.find((t) => !targets.has(t.id));
  while (tab && !ordered.includes(tab)) {
    ordered.push(tab);
    tab = byId.get(next.get(tab.id) ?? "");
  }
  return ordered.length === form.tabs.length
    ? { tabs: ordered, consistent: true }
    : { tabs: form.tabs, consistent: false };
}

// Queries read answers from field.__userAnswer, the way eUsługa exposes them.
export async function evaluateStates(
  form: FormJson,
  answers: Answers,
): Promise<Record<string, FieldStatus>> {
  const data = structuredClone(form);
  const fields = data.tabs.flatMap((t) => allFields(t.questions));
  for (const field of fields)
    Object.assign(field, { __userAnswer: answers[field.id] });

  const statuses: Record<string, FieldStatus> = {};
  for (const field of fields) {
    if (!field.states?.length) continue;
    const status: FieldStatus = { show: true, readOnly: false };
    for (const state of field.states) {
      try {
        const result = Boolean(await jsonata(state.query).evaluate(data));
        if (state.type === "SHOW") status.show &&= result;
        if (state.type === "READ_ONLY") status.readOnly ||= result;
      } catch {
        status.failedQuery = state.query;
      }
    }
    statuses[field.id] = status;
  }
  return statuses;
}

// shortcut: plain text only (links and formatting dropped), so untrusted HTML never reaches the DOM; upgrade with a sanitizer ADR.
export function htmlToText(html: string | null | undefined): string {
  if (!html) return "";
  const doc = new DOMParser().parseFromString(html, "text/html");
  return doc.body.textContent?.trim() ?? "";
}
