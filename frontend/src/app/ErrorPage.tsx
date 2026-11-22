/** Route errorElement: an unexpected render error shows this instead of a blank page. */
export function ErrorPage() {
  return (
    <main className="page page--narrow">
      <title>Błąd – forms2json</title>
      <div className="alert alert--error" role="alert">
        <span className="i i-x-circle" aria-hidden="true"></span>
        <p className="alert__title">Coś poszło nie tak</p>
        <p>
          Ten ekran napotkał nieoczekiwany błąd. Odśwież stronę albo wróć do
          listy zadań.
        </p>
        <div className="alert__actions">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => location.reload()}
          >
            <span className="i i-refresh" aria-hidden="true"></span>Odśwież
          </button>
          {/* A full page load, so nothing from the broken screen survives. */}
          <a className="btn btn--secondary" href="/">
            <span className="i i-arrow-left" aria-hidden="true"></span>Wróć do
            zadań
          </a>
        </div>
      </div>
    </main>
  );
}
