import { jsonLanguage } from "@codemirror/lang-json";
import { elementPath, type FormJson } from "../form-preview";
import { REVIEW_THRESHOLD } from "../../shared/confidence";

type Tree = ReturnType<typeof jsonLanguage.parser.parse>;
type SyntaxNode = Tree["topNode"];

// Job result contract (issue #54, backend PR #100). OpenAPI types `result` as unknown, so it is described here.
export interface ReviewIssue {
  code: string;
  message: string;
  path: string;
  severity: "ERROR" | "WARNING" | "INFO";
}

export interface ReviewResult {
  form: FormJson;
  confidence: {
    overall: number;
    elements: Record<string, number>;
    to_review: string[];
  };
  issues: ReviewIssue[];
  /** The document text the model read (#132); missing in results from before it. */
  source_text?: string;
}

/** The API result after a shape check at the trust boundary; null when it is not a review result. */
export function asReviewResult(value: unknown): ReviewResult | null {
  const r = value as Partial<ReviewResult> | null;
  return r &&
    typeof r.form === "object" &&
    typeof r.confidence?.overall === "number" &&
    typeof r.confidence.elements === "object" &&
    Array.isArray(r.confidence.to_review) &&
    Array.isArray(r.issues)
    ? (r as ReviewResult)
    : null;
}

export interface Problem {
  kind: "error" | "check";
  message: string;
  path: string;
  confidence?: number;
}

/** Errors first, then warnings, then elements below the threshold from the least certain. */
export function buildProblems(result: ReviewResult): Problem[] {
  const { elements, to_review } = result.confidence;
  const issues: Problem[] = result.issues.map((issue) => ({
    kind: issue.severity === "ERROR" ? "error" : "check",
    message: issue.message,
    path: issue.path,
    confidence: elements[issue.path] ?? elements[elementPath(issue.path)],
  }));
  const uncertain: Problem[] = to_review
    .map((path) => ({
      kind: "check" as const,
      message: "Niepewny odczyt. Porównaj element z blankietem.",
      path,
      confidence: elements[path],
    }))
    .sort((a, b) => (a.confidence ?? 1) - (b.confidence ?? 1));
  return [
    ...issues.filter((p) => p.kind === "error"),
    ...issues.filter((p) => p.kind === "check"),
    ...uncertain,
  ];
}

export const isUncertain = (
  p: Problem,
): p is Problem & { confidence: number } =>
  p.confidence !== undefined && p.confidence < REVIEW_THRESHOLD;

export const pathSegments = (path: string) => path.match(/[^.[\]]+/g) ?? [];

/** The value at a JSON path ("tabs[0].questions[1].field"); undefined when it is gone. */
export function getAt(data: unknown, path: string): unknown {
  let node = data;
  for (const segment of pathSegments(path))
    node = (node as Record<string, unknown> | null | undefined)?.[segment];
  return node;
}

/** A copy of `data` with `value` at an existing JSON path. */
export function setAt<T>(data: T, path: string, value: unknown): T {
  const copy = structuredClone(data);
  const segments = pathSegments(path);
  const last = segments.pop();
  const parent = getAt(copy, segments.join(".")) as Record<string, unknown>;
  if (last !== undefined) parent[last] = value;
  return copy;
}

/** Field types seen in the reference forms (data/, wzorce 1–9), with the words a clerk uses. */
export const FIELD_TYPES: Record<string, string> = {
  TEXT_FIELD: "Pole tekstowe",
  TEXTAREA: "Pole tekstowe wielowierszowe",
  NUMBER: "Liczba",
  DATEPICKER: "Data",
  SELECT: "Lista rozwijana",
  RADIO: "Jednokrotny wybór",
  CHECKBOX: "Pola wyboru",
  FILE_UPLOADER: "Załącznik",
  SECTION: "Sekcja",
  REPEATING_SECTION: "Sekcja powtarzalna",
  TEXT_BLOCK: "Tekst informacyjny",
  CONSENT_SECTION: "Zgody",
};

export const fieldTypeLabel = (type: string) => FIELD_TYPES[type] ?? type;

/** "Informacje o budynku, Lokalizacja budynku, Miejscowość": titles of the page and fields on the path. */
export function describePath(form: unknown, path: string): string {
  const titles: string[] = [];
  let node = form;
  let previous = "";
  for (const segment of pathSegments(path)) {
    node = (node as Record<string, unknown> | null)?.[segment];
    const title = (node as { title?: unknown } | null)?.title;
    if (
      (previous === "tabs" || segment === "field") &&
      typeof title === "string"
    )
      titles.push(title);
    previous = segment;
  }
  return titles.join(", ") || (path === "title" ? "Tytuł formularza" : path);
}

/** Offsets of the value at a JSON path in the text the tree was parsed from; null when it is gone. */
export function locate(
  tree: Tree,
  read: (from: number, to: number) => string,
  path: string,
): { from: number; to: number } | null {
  let node: SyntaxNode | null = tree.topNode.firstChild;
  for (const segment of pathSegments(path)) {
    if (node?.name === "Object") {
      const key = JSON.stringify(segment);
      node =
        node.getChildren("Property").find((p) => {
          const name = p.getChild("PropertyName");
          return name && read(name.from, name.to) === key;
        })?.lastChild ?? null;
    } else if (node?.name === "Array") {
      const items: SyntaxNode[] = [];
      for (let c = node.firstChild; c; c = c.nextSibling)
        if (!"[],".includes(c.name) && !c.type.isError) items.push(c);
      node = items[Number(segment)] ?? null;
    } else return null;
  }
  return node && { from: node.from, to: node.to };
}

// The official schema uses only type/properties/items, like the backend's check (standards.py), so no library.
export interface FormSchema {
  type?: string;
  properties?: Record<string, FormSchema>;
  items?: FormSchema;
}

/** K-09: the schema says "repetingSectionGrid"; we generate "repeatingSectionGrid", as the backend does. */
export const fixSchemaTypo = (schema: unknown): FormSchema =>
  JSON.parse(
    JSON.stringify(schema).replace(
      '"repetingSectionGrid"',
      '"repeatingSectionGrid"',
    ),
  );

const TYPE_NAMES: Record<string, string> = {
  object: "obiekt",
  array: "lista",
  string: "tekst",
  number: "liczba",
  boolean: "wartość logiczna",
};

const hasType = (value: unknown, type: string) =>
  type === "object"
    ? typeof value === "object" && value !== null && !Array.isArray(value)
    : type === "array"
      ? Array.isArray(value)
      : typeof value === type;

export function schemaIssues(
  value: unknown,
  schema: FormSchema,
  path = "",
): { path: string; message: string }[] {
  if (schema.type && !hasType(value, schema.type))
    return [
      {
        path,
        message: `„${path || "(dokument)"}” powinno mieć typ ${TYPE_NAMES[schema.type] ?? schema.type}.`,
      },
    ];
  const issues = [];
  if (schema.properties && hasType(value, "object"))
    for (const [key, sub] of Object.entries(schema.properties)) {
      const record = value as Record<string, unknown>;
      if (key in record)
        issues.push(
          ...schemaIssues(record[key], sub, path ? `${path}.${key}` : key),
        );
    }
  const { items } = schema;
  if (items && Array.isArray(value))
    value.forEach((item, i) =>
      issues.push(...schemaIssues(item, items, `${path}[${i}]`)),
    );
  return issues;
}

export interface JsonCheck {
  data?: unknown;
  syntaxError?: { line: number; from: number };
  schemaErrors: { path: string; message: string; line: number; from: number }[];
}

/** Syntax and schema check of the editor text, with line numbers for the messages. */
export function checkJson(text: string, schema: FormSchema): JsonCheck {
  const tree = jsonLanguage.parser.parse(text);
  const lineAt = (pos: number) => text.slice(0, pos).split("\n").length;
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    let from = text.length;
    tree.iterate({
      enter: (node) => {
        if (node.type.isError) from = Math.min(from, node.from);
        return from === text.length;
      },
    });
    return { syntaxError: { line: lineAt(from), from }, schemaErrors: [] };
  }
  const read = (from: number, to: number) => text.slice(from, to);
  const schemaErrors = schemaIssues(data, schema).map((issue) => {
    const from = locate(tree, read, issue.path)?.from ?? 0;
    return { ...issue, from, line: lineAt(from) };
  });
  return { data, schemaErrors };
}

/** "Wniosek o wydanie zaświadczenia" → "wniosek-o-wydanie-zaswiadczenia.json". */
export function downloadName(title: unknown): string {
  const slug = String(title ?? "")
    .replace(/ł/g, "l")
    .replace(/Ł/g, "L")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^A-Za-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  return `${slug || "formularz"}.json`;
}

/** Polish plural: plural(2, ["błąd", "błędy", "błędów"]) → "2 błędy". */
export function plural(n: number, [one, few, many]: [string, string, string]) {
  const tens = n % 100;
  const units = n % 10;
  const word =
    n === 1
      ? one
      : units >= 2 && units <= 4 && (tens < 12 || tens > 14)
        ? few
        : many;
  return `${n} ${word}`;
}
