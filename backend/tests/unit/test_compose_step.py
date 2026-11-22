from collections import Counter
from pathlib import Path

import pytest

from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.domain import rules
from forms2json.domain.form_definition import Field, FormDefinition, JsonObject, JsonValue, Question
from forms2json.domain.form_draft import FormDraft
from forms2json.domain.rules import Severity, check_rules
from forms2json.domain.standards import check_standards
from tests.evals.metrics import score

DATA = Path(__file__).parents[3] / "data"
KINDS = [{"kind": k, "confidence": 1.0} for k in ("SELF", "OTHER_PERSON", "LEGAL_ENTITY")]


def _field(
    key: str, label: str, section: str, type_: str = "TEXT_FIELD", **extra: JsonValue
) -> JsonValue:
    field: JsonObject = {
        "key": key,
        "label": label,
        "section": section,
        "type": type_,
        "required": True,
        "options": [],
        "confidence": 0.9,
    }
    return field | extra


def _draft(title: str, addressee: str, fields: list[JsonValue], **extra: JsonValue) -> FormDraft:
    base = {
        "title": {"value": title, "confidence": 1.0},
        "addressee": {"value": addressee, "confidence": 1.0},
        "applicants": KINDS,
        "fields": fields,
        "conditions": [],
        "attachments": [],
        "fees": [],
        "consents": [],
    }
    return FormDraft.model_validate(base | extra)


ZWROT = "Zwrócić przelewem na rachunek bankowy"
ZALICZ = "Zaliczyć na poczet przyszłego zobowiązania podatkowego"
OVERPAYMENT = "Informacje o nadpłacie"
SETTLEMENT = "Rozliczenie nadpłaty"
# Hand-made draft of reference 5, as the Understand step should read the source document.
DRAFT_5 = _draft(
    "Wniosek o stwierdzenie nadpłaty podatku",
    "Urząd Miasta",
    [
        _field("podatek", "Podatek, którego dotyczy nadpłata", OVERPAYMENT),
        _field("kwota", "Kwota", OVERPAYMENT, "NUMBER"),
        _field("uzasadnienie", "Uzasadnienie", OVERPAYMENT, "TEXTAREA"),
        _field(
            "co", "Wybierz, co mamy zrobić z nadpłatą", SETTLEMENT, "RADIO", options=[ZALICZ, ZWROT]
        ),
        _field("nazwa", "Nazwa podatku", SETTLEMENT),
        _field("rachunek", "Numer rachunku", SETTLEMENT, confidence=0.8),
    ],
    conditions=[
        {"target": "nazwa", "source": "co", "value": ZALICZ, "confidence": 1.0},
        {"target": "rachunek", "source": "co", "value": ZWROT, "confidence": 0.6},
    ],
    attachments=[{"name": "Plik deklaracji podatkowej", "required": True, "confidence": 0.7}],
)
BUILDING = "Lokalizacja budynku"
DRAFT_1 = _draft(
    "Wniosek o ustalenie numeru porządkowego nieruchomości",
    "Do Wójta Gminy",
    [
        _field("miejscowosc", "Miejscowość", BUILDING),
        _field("obreb", "Obręb", BUILDING),
        _field("dzialka", "Numer ewidencyjny działki", BUILDING),
        _field("ulica", "Ulica", BUILDING),
    ],
)


def _fields(form: FormDefinition) -> list[Field]:
    def walk(questions: list[Question]) -> list[Field]:
        return [f for q in questions for f in (q.field, *walk(q.field.repeating_section_grid))]

    return [f for tab in form.tabs for f in walk(tab.questions)]


def _paths(form: FormDefinition) -> list[tuple[str, Field]]:
    return [(p.path, p.field) for p in rules._walk(form)]


def _reference(number: int) -> FormDefinition:
    (path,) = DATA.glob(f"{number}. */konfiguracja_form_*.json")
    return FormDefinition.from_json(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("draft", "number"), [(DRAFT_1, 1), (DRAFT_5, 5)], ids=["1", "5"])
def test_draft_composes_close_to_reference(draft: FormDraft, number: int) -> None:
    form = ComposeStep().run(draft)

    issues = check_rules(form) + check_standards(form)
    assert [i for i in issues if i.severity is Severity.ERROR] == []
    scores = score(form, _reference(number))
    assert scores.rule_errors == 0
    assert scores.section_recall >= 0.8
    assert scores.field_recall >= 0.8
    assert scores.type_accuracy == 1.0


def test_pages_keep_standard_order_and_linear_flow() -> None:
    form = ComposeStep().run(DRAFT_5)

    assert [t.title for t in form.tabs] == [
        "Dane",
        OVERPAYMENT,
        "Kontakt i zgody",
        "Strona końcowa",
    ]
    assert [(link.source, link.target) for link in form.links] == [
        (a.id, b.id) for a, b in zip(form.tabs, form.tabs[1:], strict=False)
    ]


def test_subject_fields_keep_document_order_and_unique_tech_names() -> None:
    form = ComposeStep().run(DRAFT_5)

    subject = form.tabs[1]
    names = [
        [c.field.title for c in sorted(s.field.repeating_section_grid, key=lambda c: c.y)]
        for s in sorted(subject.questions, key=lambda q: q.y)
    ]
    assert names == [
        ["Podatek, którego dotyczy nadpłata", "Kwota", "Uzasadnienie"],
        ["Wybierz, co mamy zrobić z nadpłatą", "Nazwa podatku", "Numer rachunku"],
        ["Plik deklaracji podatkowej"],
    ]
    counts = Counter(f.tech_name for f in _fields(form))
    assert [name for name, n in counts.items() if n > 1] == []


def test_condition_gives_show_state_matching_reference() -> None:
    step = ComposeStep()
    form = step.run(DRAFT_5)

    golden = {f.tech_name: f.states for f in _fields(_reference(5))}
    for name in ("nazwa_podatku", "numer_rachunku"):
        states = next(f.states for f in _fields(form) if f.tech_name == name)
        assert states == golden[name]
        assert states is not None and [s.type for s in states] == ["SHOW"]
    paths = {f.tech_name: path for path, f in _paths(form)}
    assert step.confidence[paths["numer_rachunku"]] == 0.6  # min of field 0.8 and condition 0.6
    assert step.confidence[paths["plik_deklaracji_podatkowej"]] == 0.7
    assert step.confidence["tabs[0].questions[0].field"] == 1.0  # predefined applicant block
    assert step.confidence["tabs[0]"] == 1.0


def test_fees_become_info_section_with_payment_proof() -> None:
    fee: JsonValue = {"description": "Opłata skarbowa", "amount": 17.0, "confidence": 0.5}
    form = ComposeStep().run(_draft("Wniosek", "Urząd", [], fees=[fee]))

    fees = form.tabs[1].questions[-1].field
    assert [c.field.type for c in fees.repeating_section_grid] == ["TEXT_BLOCK", "FILE_UPLOADER"]
    assert "Opłata skarbowa: 17,00 zł" in fees.repeating_section_grid[0].field.description
    assert [i for i in check_rules(form) if i.severity is Severity.ERROR] == []


def test_draft_without_subject_fields_skips_the_subject_page() -> None:
    form = ComposeStep().run(_draft("Wniosek", "Urząd", []))

    assert [t.title for t in form.tabs] == ["Dane", "Kontakt i zgody", "Strona końcowa"]


JOINT = "Wspólność majątkowa"
SPOUSE = "Dane współmałżonka"
# Generic draft: someone else's name and address, both shown only for one answer.
DRAFT_SPOUSE = _draft(
    "Deklaracja",
    "Urząd",
    [
        _field("rodzaj", "Wybierz rodzaj własności", SPOUSE, "RADIO", options=[JOINT, "Inna"]),
        _field("wspolmalzonek", "Imię i nazwisko współmałżonka", SPOUSE, "PERSON"),
        _field(
            "malzonek_adres", "Adres zamieszkania współmałżonka", SPOUSE, "ADDRESS", confidence=0.7
        ),
    ],
    conditions=[
        {"target": key, "source": "rodzaj", "value": JOINT, "confidence": 0.8}
        for key in ("wspolmalzonek", "malzonek_adres")
    ],
)


def test_person_and_address_expand_into_standard_blocks_with_suffix() -> None:
    step = ComposeStep()
    form = step.run(DRAFT_SPOUSE)

    sections = sorted(form.tabs[1].questions, key=lambda q: q.y)
    assert [s.field.title for s in sections] == [SPOUSE, "Adres zamieszkania współmałżonka"]
    person = [c.field for c in sections[0].field.repeating_section_grid][1:]
    assert [(f.tech_name, f.title) for f in person] == [
        ("imie_wspolmalzonek", "Imię"),
        ("nazwisko_wspolmalzonek", "Nazwisko"),
    ]
    address = {c.field.tech_name: c.field for c in sections[1].field.repeating_section_grid}
    assert address["kraj_malzonek"].dictionary_name == "Kraje"
    assert address["wojewodztwo_malzonek"].dictionary_name == "TERYT_4G_DOWODOWY"
    assert all(f.default_value_type is None for f in address.values())  # no registry data
    # Country conditions follow the new names and page.
    query = (address["ulica_malzonek"].states or [])[0].query
    assert "'Dane współmałżonka' in title" in query and "'kraj_malzonek' in" in query
    for shown in (*person, sections[1].field):
        assert [s.type for s in shown.states or []] == ["SHOW"]
    paths = {f.tech_name: path for path, f in _paths(form)}
    assert step.confidence[paths["ulica_malzonek"]] == 0.7
    assert [i for i in check_rules(form) if i.severity is Severity.ERROR] == []


def test_page_splits_subject_tabs_and_condition_value_names_the_option() -> None:
    options: list[JsonValue] = ["1. właściciel", "2. współwłaściciel (wspólność majątkowa)"]
    draft = _draft(
        "Deklaracja",
        "Prezydent Miasta",
        [
            _field("typ", "Wybierz typ", "Składający", "RADIO", options=options, page="Strona A"),
            _field("malzonek", "Dane współmałżonka", "Współmałżonek", "PERSON", page="Strona A"),
            _field("kwota", "Kwota", "Opłata", "NUMBER", page="Strona B"),
        ],
        conditions=[{"target": "malzonek", "source": "typ", "value": "2", "confidence": 0.9}],
    )
    form = ComposeStep().run(draft)

    assert [t.title for t in form.tabs[1:-2]] == ["Strona A", "Strona B"]
    imie = next(f for f in _fields(form) if f.tech_name == "imie_malzonek")
    assert imie.states and imie.states[0].query.startswith(
        "(\"2. współwłaściciel (wspólność majątkowa)\" in tabs['Strona A' in title]"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [("2", "2. b (x)"), ("b", "2. b (x)"), ("2. b (x)", "2. b (x)"), ("9", "9"), ("Tak", "Tak")],
)
def test_option_for(value: str, expected: str) -> None:
    from forms2json.domain.compose import option_for

    assert option_for(value, ["1. a", "2. b (x)"]) == expected
