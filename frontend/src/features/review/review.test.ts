import { jsonLanguage } from "@codemirror/lang-json";
import { expect, test } from "vitest";
import {
  asReviewResult,
  buildProblems,
  checkJson,
  describePath,
  downloadName,
  fixSchemaTypo,
  locate,
  plural,
  type ReviewResult,
} from "./review";
import wynik from "./fixtures/wynik-wzorzec-1.json";
import { FORM_SCHEMA } from "../../test/server";

const result = wynik as ReviewResult;
const schema = fixSchemaTypo(FORM_SCHEMA);

test("locate znajduje wartość po ścieżce w tekście JSON-a", () => {
  const text = JSON.stringify(
    {
      tabs: [
        { questions: [{ field: { title: "A" } }, { field: { title: "B" } }] },
      ],
    },
    null,
    2,
  );
  const tree = jsonLanguage.parser.parse(text);
  const read = (a: number, b: number) => text.slice(a, b);
  const at = locate(tree, read, "tabs[0].questions[1].field") ?? {
    from: 0,
    to: 0,
  };
  expect(JSON.parse(text.slice(at.from, at.to))).toEqual({ title: "B" });
  expect(locate(tree, read, "tabs[0].questions[5].field")).toBeNull();
  expect(locate(tree, read, "brak")).toBeNull();
});

test("checkJson: błąd składni z linią, błąd schematu z linią, poprawny JSON", () => {
  expect(
    checkJson('{\n  "title": "A",\n  "tabs": [\n}', schema).syntaxError?.line,
  ).toBe(4);
  const wrongType = checkJson('{\n  "title": "A",\n  "tabs": {}\n}', schema);
  expect(wrongType.schemaErrors).toEqual([
    {
      path: "tabs",
      message: "„tabs” powinno mieć typ lista.",
      from: expect.any(Number),
      line: 3,
    },
  ]);
  expect(checkJson(JSON.stringify(result.form), schema).schemaErrors).toEqual(
    [],
  );
});

test("literówka schematu K-09: repeatingSectionGrid sprawdzamy pod poprawną nazwą", () => {
  const form = structuredClone(result.form) as unknown as {
    tabs: { questions: { field: Record<string, unknown> }[] }[];
  };
  form.tabs[0].questions[0].field.repeatingSectionGrid = "zła wartość";
  expect(checkJson(JSON.stringify(form), schema).schemaErrors[0].path).toBe(
    "tabs[0].questions[0].field.repeatingSectionGrid",
  );
});

test("problemy: najpierw błędy, potem ostrzeżenia, potem niepewne od najniższej pewności", () => {
  const problems = buildProblems(result);
  expect(problems.map((p) => [p.kind, p.confidence])).toEqual([
    ["error", 0.98],
    ["check", 0.98],
    ["check", 0.41],
    ["check", 0.52],
    ["check", 0.74],
  ]);
  expect(describePath(result.form, "title")).toBe("Tytuł formularza");
  expect(describePath(result.form, problems[2].path)).toBe(
    "Informacje o budynku, Lokalizacja budynku, Miejscowość",
  );
});

test("kształt wyniku, nazwa pliku i odmiana", () => {
  expect(asReviewResult(result)).toBe(result);
  expect(asReviewResult({ title: "Wniosek" })).toBeNull();
  expect(asReviewResult(null)).toBeNull();
  expect(downloadName("Wniosek o wydanie zaświadczenia – Łódź")).toBe(
    "wniosek-o-wydanie-zaswiadczenia-lodz.json",
  );
  expect(downloadName("")).toBe("formularz.json");
  expect(
    [1, 2, 5, 12, 22].map((n) => plural(n, ["błąd", "błędy", "błędów"])),
  ).toEqual(["1 błąd", "2 błędy", "5 błędów", "12 błędów", "22 błędy"]);
});
