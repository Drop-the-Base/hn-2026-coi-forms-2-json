// Same rules as backend domain/upload.py; content vs extension (FR-03) is checked only by the API.
export const EXTENSIONS = [
  ".pdf",
  ".doc",
  ".docx",
  ".ods",
  ".xlsx",
  ".jpg",
  ".jpeg",
  ".png",
];
const MAX_NAME_LENGTH = 250;
const FORBIDDEN_CHARS = ";:><\\/|'*%$";

const number = new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 1 });

export function formatBytes(bytes: number): string {
  const mb = bytes / 1024 / 1024;
  return mb < 1
    ? `${number.format(Math.ceil(bytes / 1024))} kB`
    : `${number.format(mb)} MB`;
}

/** Problems with the file, in Polish, ready to show; empty when the file can be sent (FR-02, FR-04, FR-05). */
export function validateFile(
  file: { name: string; size: number },
  maxBytes: number,
): string[] {
  const problems: string[] = [];
  const dot = file.name.lastIndexOf(".");
  const extension = dot > 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!EXTENSIONS.includes(extension)) {
    problems.push(
      extension
        ? `Format ${extension.slice(1).toUpperCase()} nie jest obsługiwany. Zapisz plik jako PDF lub DOCX.`
        : "Plik nie ma rozszerzenia. Obsługiwane: PDF, DOC, DOCX, ODS, XLSX, JPG, PNG.",
    );
  }
  // Spread counts characters like Python's len(), not UTF-16 units.
  const length = [...file.name].length;
  if (length > MAX_NAME_LENGTH) {
    problems.push(
      `Nazwa ma ${length} znaków, limit to ${MAX_NAME_LENGTH}. Skróć nazwę pliku.`,
    );
  }
  const forbidden = [...FORBIDDEN_CHARS].filter((char) =>
    file.name.includes(char),
  );
  if (forbidden.length) {
    problems.push(
      `Nazwa zawiera niedozwolony znak ${forbidden.map((char) => `„${char}”`).join(", ")}.`,
    );
  }
  if (file.size > maxBytes) {
    problems.push(
      `Plik ma ${formatBytes(file.size)}, limit to ${formatBytes(maxBytes)}. Zmniejsz rozdzielczość skanu.`,
    );
  }
  return problems;
}
