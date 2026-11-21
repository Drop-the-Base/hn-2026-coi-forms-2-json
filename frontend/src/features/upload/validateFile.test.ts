import { expect, test } from "vitest";
import { formatBytes, validateFile } from "./validateFile";

const MB = 1024 * 1024;

test.each([
  "a.pdf",
  "A.PDF",
  "b.DOC",
  "c.docx",
  "d.ods",
  "e.xlsx",
  "f.JPG",
  "g.jpeg",
  "h.png",
])("%s przechodzi", (name) =>
  expect(validateFile({ name, size: 10 }, 20 * MB)).toEqual([]),
);

test("zły format, brak rozszerzenia, plik ukryty", () => {
  expect(validateFile({ name: "notatka.txt", size: 1 }, MB)[0]).toContain(
    "Format TXT",
  );
  expect(validateFile({ name: "wniosek", size: 1 }, MB)[0]).toContain(
    "nie ma rozszerzenia",
  );
  expect(validateFile({ name: ".pdf", size: 1 }, MB)).toHaveLength(1);
});

test("nazwa: limit 250 znaków liczony jak w Pythonie i zakazane znaki", () => {
  expect(validateFile({ name: `${"ą".repeat(246)}.pdf`, size: 1 }, MB)).toEqual(
    [],
  );
  expect(validateFile({ name: `${"a".repeat(247)}.pdf`, size: 1 }, MB)).toEqual(
    ["Nazwa ma 251 znaków, limit to 250. Skróć nazwę pliku."],
  );
  expect(validateFile({ name: "a;b%c.pdf", size: 1 }, MB)).toEqual([
    "Nazwa zawiera niedozwolony znak „;”, „%”.",
  ]);
});

test("rozmiar: limit włącznie, komunikat z obiema liczbami", () => {
  expect(validateFile({ name: "a.pdf", size: 20 * MB }, 20 * MB)).toEqual([]);
  expect(validateFile({ name: "a.pdf", size: 34.2 * MB }, 20 * MB)).toEqual([
    "Plik ma 34,2 MB, limit to 20 MB. Zmniejsz rozdzielczość skanu.",
  ]);
  expect(formatBytes(412 * 1024)).toBe("412 kB");
});
