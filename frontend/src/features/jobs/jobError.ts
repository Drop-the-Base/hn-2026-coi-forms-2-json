// The worker reports a failed job only by its error type (process_job.py); the Polish text lives here.
const MESSAGES: Record<string, string> = {
  UnsupportedFormat:
    "Ten format pliku nie jest jeszcze obsługiwany. Zapisz blankiet jako PDF, DOCX albo XLSX i wgraj ponownie.",
  ExtractionFailed:
    "Nie udało się odczytać treści pliku. Sprawdź, czy nie jest uszkodzony, zaszyfrowany ani za długi, i wgraj ponownie.",
  DocumentTooLong:
    "Blankiet jest za długi do przetworzenia w całości. Podziel go na mniejsze pliki.",
  LlmCallFailed:
    "Model językowy nie odpowiedział poprawnie. Wgraj plik ponownie za kilka minut.",
  LlmRequestTooLarge:
    "Formularz jest za duży dla limitu dostawcy modelu językowego (np. darmowego planu). Podziel blankiet na mniejsze pliki albo użyj modelu z wyższym limitem.",
  LlmRateLimited:
    "Wyczerpano limit zapytań do modelu językowego. Odczekaj minutę i wgraj plik ponownie.",
  InvalidFormDraft:
    "Model zwrócił formularz, którego nie da się odczytać. Wgraj plik ponownie.",
  InvalidFormDefinition:
    "Model zwrócił formularz, którego nie da się odczytać. Wgraj plik ponownie.",
};

export const jobErrorMessage = (type: string | null | undefined) =>
  MESSAGES[type ?? ""] ??
  `Nie udało się przetworzyć pliku${type ? ` (kod: ${type})` : ""}. Wgraj plik ponownie.`;
