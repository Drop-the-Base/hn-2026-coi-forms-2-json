"""Runs forms 1-9 through the running app and scores them (ADR-0010, FR-T4).

uv run python -m tests.evals.run_eval --forms 3 --name groq-1 [--baseline groq-0]   (in backend/)
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any

import httpx2

from forms2json.domain.form_definition import FormDefinition
from tests.evals.metrics import score

DATA = Path(__file__).parents[3] / "data"
GOLDEN = Path(__file__).parent / "dataset" / "golden"
RUNS = Path(__file__).parent / "runs"
SOURCE_SUFFIXES = (".docx", ".pdf", ".ods", ".xlsx")
POLL_SECONDS = 2.0

# (header, key in a row, format); every key except status/error is a number.
COLUMNS = [
    ("błędy reguł", "rule_errors", "{:.0f}"),
    ("sekcje P", "section_precision", "{:.2f}"),
    ("sekcje R", "section_recall", "{:.2f}"),
    ("sekcje F1", "section_f1", "{:.2f}"),
    ("pola P", "field_precision", "{:.2f}"),
    ("pola R", "field_recall", "{:.2f}"),
    ("pola F1", "field_f1", "{:.2f}"),
    ("typy", "type_accuracy", "{:.2f}"),
    ("warunki", "condition_accuracy", "{:.2f}"),
    ("confidence", "confidence", "{:.2f}"),
    ("czas s", "seconds", "{:.0f}"),
    ("tokeny", "tokens", "{:.0f}"),
]

type Row = dict[str, Any]


def form_dir(n: int) -> Path:
    return next(DATA.glob(f"{n}. *"))


def source_file(directory: Path) -> Path:
    """The blank form: DOCX, then PDF, then ODS/XLSX; COI's visualisations are not inputs."""
    files = [f for f in directory.iterdir() if "wizualizacja" not in f.name]
    for suffix in SOURCE_SUFFIXES:
        for f in sorted(files):
            if f.suffix.lower() == suffix:
                return f
    raise FileNotFoundError(f"no DOCX/PDF/ODS/XLSX in {directory}")


def golden_file(n: int) -> Path:
    # Forms 1 and 5 come with COI's reference JSON; the rest have our goldens.
    if n in (1, 5):
        return next(form_dir(n).glob("konfiguracja_form_*.json"))
    return GOLDEN / f"{n}.json"


def run_job(client: httpx2.Client, path: Path, timeout: float) -> dict[str, Any]:
    """The job status ({status, result | error}); HTTP errors and timeouts count as failed."""
    response = client.post("/api/v1/jobs", files={"file": (path.name, path.read_bytes())})
    if response.status_code != 202:
        return {"status": "failed", "error": f"HTTP {response.status_code}"}
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job: dict[str, Any] = client.get(f"/api/v1/jobs/{job_id}").raise_for_status().json()
        if job["status"] != "pending":
            return job
        time.sleep(POLL_SECONDS)
    return {"status": "failed", "error": "Timeout"}


def score_row(job: dict[str, Any], golden: FormDefinition, seconds: float) -> Row:
    result = job.get("result") or {}
    # A failed job scores as an empty form: zero recall, with its error type in the table.
    form = FormDefinition.from_dict(result["form"]) if "form" in result else FormDefinition("")
    s = score(form, golden)
    usage = result.get("usage", {})
    # An empty prediction would get precision 1.0 (nothing wrong predicted) and lift the average.
    precision = 1.0 if job["status"] == "done" else 0.0
    return {
        "status": job["status"],
        "error": job.get("error"),
        "rule_errors": s.rule_errors,
        "section_precision": s.section_precision * precision,
        "section_recall": s.section_recall,
        "section_f1": s.section_f1,
        "field_precision": s.field_precision * precision,
        "field_recall": s.field_recall,
        "field_f1": s.field_f1,
        "type_accuracy": s.type_accuracy,
        "condition_accuracy": s.condition_accuracy,
        "confidence": result.get("confidence", {}).get("overall"),
        "seconds": seconds,
        "tokens": usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
    }


def with_average(rows: dict[str, Row]) -> dict[str, Row]:
    average: Row = {"status": "", "error": None}
    for _, key, _ in COLUMNS:
        values = [r[key] for r in rows.values() if r.get(key) is not None]
        average[key] = fmean(values) if values else None
    return {**rows, "średnia": average}


def to_markdown(rows: dict[str, Row], baseline: dict[str, Row] | None = None) -> str:
    """One row per form plus the average; with a baseline each number gets its delta."""
    rows = with_average(rows)
    if baseline is not None:
        baseline = with_average({k: v for k, v in baseline.items() if k in rows})
    lines = [
        "| formularz | status | " + " | ".join(h for h, _, _ in COLUMNS) + " |",
        "|---" * (len(COLUMNS) + 2) + "|",
    ]
    for name, row in rows.items():
        status = row["error"] or row["status"]
        cells = [name, status]
        for _, key, fmt in COLUMNS:
            value = row.get(key)
            cell = "-" if value is None else fmt.format(value)
            before = (baseline or {}).get(name, {}).get(key)
            if value is not None and before is not None:
                cell += f" ({fmt.replace(':', ':+').format(value - before)})"
            cells.append(cell)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forms", default="1,2,3,4,5,6,7,8,9", help="np. 1,3")
    parser.add_argument("--name", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--baseline", help="nazwa zapisanego przebiegu z runs/")
    parser.add_argument(
        "--api-url", default=os.environ.get("EVAL_API_URL", "http://localhost:8080")
    )
    parser.add_argument("--token-file", type=Path, help="plik z JWT (inaczej EVAL_TOKEN)")
    parser.add_argument("--delay", type=float, default=5.0, help="sekundy między formularzami")
    parser.add_argument("--timeout", type=float, default=900.0, help="sekundy na zadanie")
    args = parser.parse_args()

    token = args.token_file.read_text().strip() if args.token_file else os.environ["EVAL_TOKEN"]
    baseline = None
    if args.baseline:
        baseline = json.loads((RUNS / args.baseline / "scores.json").read_text(encoding="utf-8"))
    out = RUNS / args.name
    out.mkdir(parents=True, exist_ok=True)
    rows: dict[str, Row] = {}
    headers = {"Authorization": f"Bearer {token}"}
    with httpx2.Client(base_url=args.api_url, headers=headers, timeout=60) as client:
        for i, n in enumerate(int(f) for f in args.forms.split(",")):
            if i:
                time.sleep(args.delay)  # provider rate limits (tokens per minute)
            source = source_file(form_dir(n))
            print(f"formularz {n}: {source.name}", flush=True)
            started = time.monotonic()
            job = run_job(client, source, args.timeout)
            seconds = time.monotonic() - started
            text = json.dumps(job.get("result", job), ensure_ascii=False, indent=2)
            (out / f"{n}.json").write_text(text, encoding="utf-8")
            golden = FormDefinition.from_json(golden_file(n).read_text(encoding="utf-8"))
            rows[str(n)] = score_row(job, golden, seconds)
            print(f"  {job['status']} {job.get('error') or ''} {seconds:.0f}s", flush=True)
    scores = json.dumps(rows, ensure_ascii=False, indent=2)
    (out / "scores.json").write_text(scores, encoding="utf-8")
    print(f"\nPrzebieg: {out}\n\n" + to_markdown(rows, baseline))


if __name__ == "__main__":
    main()
