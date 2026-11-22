import { useCallback, useState } from "react";
import { sourceFiles } from "../../shared/sourceFiles";
import { usePreviewPdf } from "./api";

/** Points the element at a blob URL of the file and revokes it when the element goes away. */
function useBlobSrc(file: Blob) {
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

function PdfView({ pdf, name }: { pdf: Blob; name: string }) {
  return (
    <iframe
      ref={useBlobSrc(pdf)}
      className="source__pdf"
      title={`Oryginał: ${name}`}
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

/** The text the model read, under a notice why the original itself is not shown. */
function TextView({
  notice,
  sourceText,
}: {
  notice: string;
  sourceText?: string;
}) {
  return (
    <div className="source__text">
      <div className="alert alert--info review-alert" role="status">
        <span className="i i-info" aria-hidden="true"></span>
        <p>
          {notice}
          {sourceText && " Poniżej tekst odczytany z dokumentu."}
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

/** DOC, DOCX, XLSX or ODS: the API renders it as PDF (ADR-0031), the text is the fallback. */
function ConvertedView({
  jobId,
  file,
  sourceText,
}: {
  jobId: string;
  file: File;
  sourceText?: string;
}) {
  const preview = usePreviewPdf(jobId, file);
  if (preview.data) return <PdfView pdf={preview.data} name={file.name} />;
  if (preview.isError) {
    return (
      <TextView
        notice="Nie udało się przygotować podglądu oryginału."
        sourceText={sourceText}
      />
    );
  }
  return (
    <p className="muted source__page" role="status">
      Przygotowuję podgląd oryginału…
    </p>
  );
}

/** The uploaded document from tab memory: PDF and images as they are, other formats via the API. */
export function SourceView({
  jobId,
  sourceText,
}: {
  jobId: string;
  sourceText?: string;
}) {
  const file = sourceFiles.get(jobId);
  if (!file) {
    return (
      <TextView
        notice="Pliku nie ma już w tej karcie (na przykład po odświeżeniu strony)."
        sourceText={sourceText}
      />
    );
  }
  if (file.type === "application/pdf")
    return <PdfView pdf={file} name={file.name} />;
  if (file.type.startsWith("image/")) return <ImageView file={file} />;
  return <ConvertedView jobId={jobId} file={file} sourceText={sourceText} />;
}
