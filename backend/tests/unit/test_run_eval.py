from pathlib import Path

from forms2json.domain.form_definition import FormDefinition
from tests.evals.run_eval import GOLDEN, golden_file, score_row, source_file, to_markdown


def _golden_3() -> FormDefinition:
    return FormDefinition.from_json(golden_file(3).read_text(encoding="utf-8"))


def test_source_prefers_docx_then_pdf_and_skips_visualisations(tmp_path: Path) -> None:
    for name in ("a.xlsx", "a.PDF", "a - wizualizacja.docx", "a.png"):
        (tmp_path / name).touch()
    assert source_file(tmp_path).name == "a.PDF"
    (tmp_path / "a.docx").touch()
    assert source_file(tmp_path).name == "a.docx"


def test_golden_is_coi_reference_for_1_and_5_and_ours_otherwise() -> None:
    assert golden_file(1).name.startswith("konfiguracja_form_")
    assert golden_file(5).name.startswith("konfiguracja_form_")
    assert golden_file(3) == GOLDEN / "3.json"


def test_failed_job_scores_zero_recall_with_its_error() -> None:
    row = score_row({"status": "failed", "error": "LlmRequestTooLarge"}, _golden_3(), 1.0)
    assert (row["field_precision"], row["field_recall"], row["tokens"]) == (0.0, 0.0, 0)
    assert "| 3 | LlmRequestTooLarge |" in to_markdown({"3": row})


def test_baseline_adds_deltas_including_the_average() -> None:
    golden = _golden_3()
    before = score_row({"status": "failed", "error": "X"}, golden, 10.0)
    now = score_row({"status": "done", "result": {"form": golden.to_dict()}}, golden, 4.0)
    table = to_markdown({"3": now}, {"3": before, "9": before}).splitlines()
    assert "| 1.00 (+1.00) |" in table[2]  # field recall 0 -> 1
    assert "| 4 (-6) |" in table[2]
    assert table[3].startswith("| średnia |")
    assert "(+1.00)" in table[3]  # form 9 is not in this run, so it stays out of the average
