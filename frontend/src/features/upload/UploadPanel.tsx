import { useState, type DragEvent } from "react";
import { sourceFiles } from "../../shared/sourceFiles";
import { useConfig, useSubmitJob } from "./api";
import { EXTENSIONS, formatBytes, validateFile } from "./validateFile";
import "./UploadPanel.css";

type Picked = { key: string; file: File; serverError?: string };

const fileKey = (file: File) =>
  `${file.name}:${file.size}:${file.lastModified}`;

function filesWord(count: number) {
  const lastTwo = count % 100;
  const last = count % 10;
  if (count === 1) return "plik";
  return last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)
    ? "pliki"
    : "plików";
}

/** Drag & drop or pick files, checked in the browser, each valid one sent as its own job (FR-E4, FR-T3). */
export function UploadPanel({
  onUploaded,
}: {
  onUploaded: (jobId: string, fileName: string) => void;
}) {
  const config = useConfig();
  const submit = useSubmitJob();
  const [picked, setPicked] = useState<Picked[]>([]);
  const [dragging, setDragging] = useState(false);
  const [sending, setSending] = useState<{ current: number; total: number }>();

  const maxBytes = config.data?.max_upload_bytes;
  const rows = picked.map((row) => ({
    ...row,
    // Until the limit arrives only name and format are checked; sending waits for it.
    problems: [
      ...validateFile(row.file, maxBytes ?? Infinity),
      ...(row.serverError ? [row.serverError] : []),
    ],
  }));
  const ready = rows.filter((row) => row.problems.length === 0);
  const skipped = rows.length - ready.length;

  function add(fileList: FileList | null) {
    // Copy now: the FileList is live and empties when the input is reset.
    const files = [...(fileList ?? [])];
    setPicked((current) => {
      const known = new Set(current.map((row) => row.key));
      const added = files
        .map((file) => ({ key: fileKey(file), file }))
        .filter((row) => !known.has(row.key));
      return [...current, ...added];
    });
  }

  const remove = (key: string) =>
    setPicked((current) => current.filter((row) => row.key !== key));

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    add(event.dataTransfer.files);
  }

  async function send() {
    for (const [index, row] of ready.entries()) {
      setSending({ current: index + 1, total: ready.length });
      try {
        const { job_id } = await submit.mutateAsync(row.file);
        sourceFiles.set(job_id, row.file);
        onUploaded(job_id, row.file.name);
        remove(row.key);
      } catch (error) {
        const message = `Serwer odrzucił plik: ${(error as Error).message}`;
        setPicked((current) =>
          current.map((item) =>
            item.key === row.key ? { ...item, serverError: message } : item,
          ),
        );
      }
    }
    setSending(undefined);
  }

  return (
    <section className="sheet" aria-labelledby="wgraj-h">
      <div className="sheet__head">
        <h2 id="wgraj-h">Wgraj formularze</h2>
      </div>
      <div className="sheet__body">
        <div
          className={dragging ? "drop drop--active" : "drop"}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <span className="i i-upload i-lg" aria-hidden="true"></span>
          <div className="drop__text">
            <strong>Przeciągnij pliki tutaj albo wybierz je z dysku</strong>
            <p id="upload-rules">
              Formaty: PDF, DOC, DOCX, ODS, XLSX, JPG, PNG.{" "}
              {maxBytes === undefined
                ? "Sprawdzamy limit rozmiaru…"
                : `Maksymalnie ${formatBytes(maxBytes)} na plik.`}{" "}
              Możesz wybrać kilka plików naraz.
            </p>
          </div>
          <input
            className="visually-hidden"
            id="pliki"
            type="file"
            multiple
            accept={EXTENSIONS.join(",")}
            aria-describedby="upload-rules"
            onChange={(event) => {
              add(event.target.files);
              event.target.value = "";
            }}
          />
          <label className="btn btn--secondary" htmlFor="pliki">
            <span className="i i-file" aria-hidden="true"></span>Wybierz pliki
          </label>
        </div>

        {config.isError && (
          <div className="alert alert--error upload__alert" role="alert">
            <span className="i i-x-circle" aria-hidden="true"></span>
            <p className="alert__title">Nie udało się pobrać limitu rozmiaru</p>
            <p>{config.error.message}</p>
            <div className="alert__actions">
              <button
                className="btn btn--secondary btn--sm"
                type="button"
                onClick={() => void config.refetch()}
              >
                <span className="i i-refresh" aria-hidden="true"></span>Spróbuj
                ponownie
              </button>
            </div>
          </div>
        )}

        {rows.length > 0 && (
          <div className="queue">
            <h3 id="kolejka-h">Wybrane pliki ({rows.length})</h3>
            <div className="table-wrap">
              <table className="table" aria-labelledby="kolejka-h">
                <thead>
                  <tr>
                    <th scope="col">Plik</th>
                    <th scope="col">Rozmiar</th>
                    <th scope="col">Sprawdzenie</th>
                    <th scope="col">
                      <span className="visually-hidden">Akcje</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.key}>
                      <td>
                        <span className="file-name">
                          <span className="i i-file" aria-hidden="true"></span>
                          {row.file.name}
                        </span>
                      </td>
                      <td className="num">{formatBytes(row.file.size)}</td>
                      <td>
                        {row.problems.length > 0 ? (
                          <span className="file-error">
                            <span
                              className="i i-x-circle"
                              aria-hidden="true"
                            ></span>
                            <span>{row.problems.join(" ")}</span>
                          </span>
                        ) : (
                          <span className="file-ok">
                            <span
                              className="i i-check"
                              aria-hidden="true"
                            ></span>
                            Gotowy do wysłania
                          </span>
                        )}
                      </td>
                      <td className="row-actions">
                        <button
                          className="btn btn--ghost btn--sm"
                          type="button"
                          disabled={sending !== undefined}
                          onClick={() => remove(row.key)}
                        >
                          Usuń z listy
                          <span className="visually-hidden">
                            : {row.file.name}
                          </span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="queue__foot">
              <button
                className="btn btn--primary"
                type="button"
                disabled={
                  ready.length === 0 ||
                  maxBytes === undefined ||
                  sending !== undefined
                }
                aria-busy={sending !== undefined}
                aria-describedby="pomijane"
                onClick={() => void send()}
              >
                <span
                  className={sending ? "i i-loader" : "i i-upload"}
                  aria-hidden="true"
                ></span>
                {sending
                  ? `Wysyłanie ${sending.current} z ${sending.total}`
                  : `Wyślij ${ready.length} ${filesWord(ready.length)}`}
              </button>
              <span className="btn-note" id="pomijane" aria-live="polite">
                {ready.length === 0
                  ? "Żaden plik nie spełnia wymagań. Popraw pliki i dodaj je ponownie."
                  : skipped > 0
                    ? `Pliki z błędami zostaną pominięte: ${skipped}. Popraw je i dodaj ponownie.`
                    : ""}
              </span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
