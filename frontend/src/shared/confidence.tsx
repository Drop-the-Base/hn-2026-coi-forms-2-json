// Confidence levels from DESIGN.md §6: below 0.85 is shown for review (medium and low).
export const REVIEW_THRESHOLD = 0.85;
const LOW_BELOW = 0.6;

export type ConfidenceLevel = "low" | "medium" | "high";

export const confidenceLevel = (value: number): ConfidenceLevel =>
  value < LOW_BELOW ? "low" : value < REVIEW_THRESHOLD ? "medium" : "high";

const WORD = { low: "Niska", medium: "Średnia", high: "Wysoka" };

export const formatConfidence = (value: number) =>
  value.toFixed(2).replace(".", ",");

/** Badge with pattern, word and number, never colour alone (NFR-15). */
export function ConfidenceBadge({ value }: { value: number }) {
  const level = confidenceLevel(value);
  return (
    <span className={`badge badge--${level}`}>
      <span className="visually-hidden">Pewność: </span>
      {WORD[level]} <span className="num">{formatConfidence(value)}</span>
    </span>
  );
}
