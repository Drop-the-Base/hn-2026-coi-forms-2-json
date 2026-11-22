from dataclasses import replace
from pathlib import Path

import pytest

from forms2json.domain.accessibility import check_accessibility, fog_index
from forms2json.domain.form_definition import Field, FormDefinition, Option, Question, Tab
from forms2json.domain.rules import Severity

DATASET = Path(__file__).parents[1] / "evals" / "dataset"
DATA = Path(__file__).parents[3] / "data"
# Training forms 1-9 only: the hold-out set (walidacja) must not shape these hints (NFR-11).
TRAINING = [
    *DATA.glob("1. */konfiguracja_form_*.json"),
    *DATA.glob("5. */konfiguracja_form_*.json"),
    *(DATASET / "golden").glob("*.json"),
]
EASY = "Wpisz imię i nazwisko. Podaj adres. Dodaj zdjęcie dowodu. Urząd odpowie w tydzień."
HARD = (
    "Organ podatkowy, na wniosek podatnika, stwierdza nadpłatę podatku w przypadku, gdy podatnik "
    "w terminie ustawowym nie dokonał zapłaty, a następnie dokonał zapłaty z zastosowaniem "
    "obowiązujących przepisów, uwzględniając odpowiednie zastosowanie przepisów dotyczących "
    "zabezpieczenia wykonania zobowiązania podatkowego."
)


def _field(type_: str, title: str = "Imię") -> Field:
    return Field(id="f", type=type_, tech_name="pole", title=title, question_order=0)


def _form(
    *fields: Field, tab_title: str = "Dane", section_title: str = "Twoje dane"
) -> FormDefinition:
    section = Field(
        id="s",
        type="SECTION",
        tech_name="sekcja",
        title=section_title,
        question_order=0,
        repeating_section_grid=[Question(0, 0, 1, 12, f) for f in fields],
    )
    return FormDefinition(
        "Wniosek", [Tab("t1", tab_title, "MAIN", [Question(0, 0, 1, 12, section)])]
    )


def _codes(form: FormDefinition) -> list[str]:
    return [i.code for i in check_accessibility(form)]


def test_fog_separates_plain_from_legal_polish() -> None:
    assert fog_index(EASY) < 6
    assert fog_index(HARD) > 20
    assert fog_index("") == 0.0


def test_clean_form_has_no_hints() -> None:
    assert check_accessibility(_form(_field("TEXT_FIELD"))) == []


def test_hints_are_info_only() -> None:
    issues = check_accessibility(_form(_field("TEXT_FIELD", ""), tab_title="Strona 2"))
    assert issues and {i.severity for i in issues} == {Severity.INFO}


def test_missing_and_long_label() -> None:
    long = "Czy " + " ".join(["bardzo"] * 20) + " długie pytanie?"
    assert _codes(_form(_field("TEXT_FIELD", " "))) == ["A-LABEL"]
    assert _codes(_form(_field("TEXT_FIELD", long))) == ["A-LABEL"]


def test_choice_with_fewer_than_two_options() -> None:
    one = [Option("o1", "Tak")]
    two = [Option("o1", "Tak"), Option("o2", "Nie")]
    assert _codes(_form(replace(_field("RADIO"), options=one))) == ["A-OPTIONS"]
    assert _codes(_form(replace(_field("RADIO"), options=two))) == []
    assert _codes(_form(replace(_field("SELECT"), dictionary_name="KRAJE"))) == []


@pytest.mark.parametrize("title", ["Strona 2", "Sekcja 1", "3", "Część II"])
def test_generic_page_and_section_titles(title: str) -> None:
    assert _codes(_form(_field("TEXT_FIELD"), tab_title=title)) == ["A-GENERIC-TITLE"]
    assert _codes(_form(_field("TEXT_FIELD"), section_title=title)) == ["A-GENERIC-TITLE"]


def test_text_wall_and_hard_text() -> None:
    wall = "<p>" + " ".join(["Wpisz dane."] * 50) + "</p>"
    split = "".join(f"<p>{EASY}</p>" for _ in range(5))
    hard = f"<p>{HARD}</p>"
    assert _codes(_form(replace(_field("TEXT_BLOCK", ""), description=wall))) == ["A-TEXT-WALL"]
    assert _codes(_form(replace(_field("TEXT_BLOCK", ""), description=split))) == []
    assert _codes(_form(replace(_field("TEXT_BLOCK", ""), description=hard))) == [
        "A-PLAIN-LANGUAGE"
    ]


@pytest.mark.parametrize("path", TRAINING, ids=lambda p: p.name[:12])
def test_training_goldens_raise_no_hints(path: Path) -> None:
    assert check_accessibility(FormDefinition.from_json(path.read_text(encoding="utf-8"))) == []
