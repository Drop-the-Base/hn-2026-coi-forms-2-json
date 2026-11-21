import { useCallback, useState } from "react";
import { sourceFiles } from "../../shared/sourceFiles";

/** Points the element at a blob URL of the file and revokes it when the element goes away. */
function useBlobSrc(file: File) {
  return useCallback(
    (el: HTMLIFrameElement | HTMLImageElement | null) => {
      if (!el) return;
      const url = URL.createObjectURL(file);
      el.src = url;
      return () => URL.revokeObjectURL(url);
    },
    [file],
  );
}

function PdfView({ file }: { file: File }) {
  return (
    <iframe
      ref={useBlobSrc(file)}
      className="source__pdf"
      title={`Oryginał: ${file.name}`}
    />
  );
}

function ImageView({ file }: { file: File }) {
  const [full, setFull] = useState(false);
  return (
    <button
      type="button"
      className="source__zoom"
      aria-pressed={full}
      onClick={() => setFull(!full)}
    >
      <img
        ref={useBlobSrc(file)}
        className={full ? "source__img source__img--full" : "source__img"}
        alt={`Oryginał: ${file.name}`}
      />
      <span className="visually-hidden">, powiększenie 100%</span>
    </button>
  );
}

/** Pages of the backend serializer's text, each starting with a "## Strona N" line. */
function pages(text: string) {
  return text
    .split(/^(?=## Strona \d+$)/m)
    .map((chunk) => {
      const [first, ...rest] = chunk.split("\n");
      const heading = first.match(/^## (Strona \d+)$/)?.[1];
      return heading ? { heading, body: rest.join("\n") } : { body: chunk };
    })
    .filter((page) => page.heading || page.body.trim());
}

/** The uploaded document: PDF and images from tab memory, anything else as the text the model read. */
export function SourceView({
  jobId,
  sourceText,
}: {
  jobId: string;
  sourceText?: string;
}) {
  const file = sourceFiles.get(jobId);
  if (file?.type === "application/pdf") return <PdfView file={file} />;
  if (file?.type.startsWith("image/")) return <ImageView file={file} />;

  return (
    <div className="source__text">
      <div className="alert alert--info review-alert" role="status">
        <span className="i i-info" aria-hidden="true"></span>
        <p>
          {file
            ? "Ten format nie ma podglądu w przeglądarce. Poniżej tekst odczytany z dokumentu."
            : "Pliku nie ma już w tej karcie (na przykład po odświeżeniu strony). Poniżej tekst odczytany z dokumentu."}
        </p>
      </div>
      {sourceText ? (
        pages(sourceText).map((page, i) => (
          <section key={i} className="source__page">
            {page.heading && <h3>{page.heading}</h3>}
            <pre>{page.body}</pre>
          </section>
        ))
      ) : (
        <p className="muted source__page">
          Wynik nie zawiera tekstu dokumentu. Wgraj plik ponownie, aby zobaczyć
          oryginał.
        </p>
      )}
    </div>
  );
}
