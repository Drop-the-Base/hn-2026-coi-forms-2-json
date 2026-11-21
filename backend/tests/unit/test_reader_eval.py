from pathlib import Path

from tests.evals.reader_eval import coverage, docx_file, to_markdown


def test_coverage_counts_reference_words_found_in_the_text() -> None:
    share, missing = coverage("Opłata skarbowa 82 zł, numer konta", "opłata skarbowa, numer")

    assert missing == ["konta"]
    assert share == 3 / 4  # "zł" and "82" are too short to count


def test_docx_file_takes_a_doc_only_when_it_is_a_docx_inside(tmp_path: Path) -> None:
    (tmp_path / "a.DOC").write_bytes(b"\xd0\xcf binary OLE2")
    (tmp_path / "a - wizualizacja.docx").write_bytes(b"PK")
    assert docx_file(tmp_path) is None
    (tmp_path / "a.DOC").write_bytes(b"PK zip")
    assert docx_file(tmp_path) == tmp_path / "a.DOC"


def test_markdown_shows_changes_against_the_baseline() -> None:
    row = {"coverage": 1.0, "checkboxes": 5, "pdf_checkboxes": 7, "list_items": 0, "footnotes": 0}
    before = {**row, "coverage": 0.965, "checkboxes": 0}

    table = to_markdown({"7": {**row, "missing": []}}, {"7": before})

    assert "| 7 | 96.5% → 100.0% | 0 → 5 | 7 | 0 | 0 |" in table
