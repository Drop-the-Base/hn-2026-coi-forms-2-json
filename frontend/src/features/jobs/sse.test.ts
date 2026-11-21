import { expect, test } from "vitest";
import { readSse } from "./sse";

function streamOf(...chunks: (string | Uint8Array)[]) {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks)
        controller.enqueue(
          typeof chunk === "string" ? encoder.encode(chunk) : chunk,
        );
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>) {
  const out: string[] = [];
  for await (const data of readSse(stream)) out.push(data);
  return out;
}

test("składa zdarzenie pocięte w środku znaku i między CR a LF", async () => {
  const bytes = new TextEncoder().encode(
    'event: progress\r\ndata: {"step":"żółw"}\r\n\r\n',
  );
  const cut = bytes.indexOf(0xc5) + 1; // inside the two-byte "ż"
  expect(
    await collect(
      streamOf(bytes.slice(0, cut), bytes.slice(cut, -3), bytes.slice(-3)),
    ),
  ).toEqual(['{"step":"żółw"}']);
});

test("pomija ping i zwraca kilka zdarzeń z jednego kawałka", async () => {
  expect(
    await collect(
      streamOf(
        ": ping\n\nevent: progress\ndata: 1\n\nevent: progress\ndata: 2\n\n",
        ": ping\n\nevent: progress\nda",
        "ta: 3\n\n",
      ),
    ),
  ).toEqual(["1", "2", "3"]);
});

test("niedokończone zdarzenie na końcu strumienia przepada", async () => {
  expect(await collect(streamOf("data: 1\n\ndata: 2\n"))).toEqual(["1"]);
});
