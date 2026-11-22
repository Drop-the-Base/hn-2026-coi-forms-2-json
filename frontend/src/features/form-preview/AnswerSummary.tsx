import { allFields, type Answers, type FormTab } from "./form";

// The e-service shows the filled-in application on its final page before signing; the preview
// lists what was typed on the earlier pages, so "sprawdź dane na podglądzie" has something to check.
export function AnswerSummary({
  tabs,
  answers,
}: {
  tabs: FormTab[];
  answers: Answers;
}) {
  const pages = tabs
    .map((tab) => ({
      tab,
      rows: allFields(tab.questions).flatMap((field) => {
        const value = answers[field.id];
        const values = Array.isArray(value) ? value : value ? [value] : [];
        if (!values.length) return [];
        const names = values.map(
          (v) =>
            field.options?.find((o) => o.id === v || o.name === v)?.name ??
            (v === "true" ? "Tak" : v),
        );
        return [
          {
            id: field.id,
            title: field.title || "Pole",
            text: names.join(", "),
          },
        ];
      }),
    }))
    .filter((p) => p.rows.length);

  return (
    <section className="eu-card eu-summary" aria-label="Wpisane dane">
      <h4>Wpisane dane</h4>
      {pages.length === 0 ? (
        <p>
          Nie wpisano jeszcze żadnych danych. Wróć do poprzednich stron i
          wypełnij pola, a pojawią się tutaj.
        </p>
      ) : (
        pages.map(({ tab, rows }) => (
          <div key={tab.id}>
            <h5>{tab.title}</h5>
            <dl>
              {rows.map((r) => (
                <div key={r.id}>
                  <dt>{r.title}</dt>
                  <dd>{r.text}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))
      )}
    </section>
  );
}
