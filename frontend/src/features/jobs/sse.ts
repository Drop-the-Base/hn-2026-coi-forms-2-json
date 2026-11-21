/**
 * Yields the `data` of each Server-Sent Event in a fetch body. Comments (the `: ping`
 * keep-alive) and other fields are skipped; our API sends no `id` and one event name.
 * Hand-written instead of a library: the subset we need is ~20 lines (ADR-0014).
 */
export async function* readSse(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    // A "\r" at the end of a chunk stays until its "\n" arrives.
    buffer = (buffer + decoder.decode(value, { stream: true })).replace(
      /\r\n/g,
      "\n",
    );
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const data = buffer
        .slice(0, end)
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).replace(/^ /, ""))
        .join("\n");
      buffer = buffer.slice(end + 2);
      if (data) yield data;
    }
  }
}
