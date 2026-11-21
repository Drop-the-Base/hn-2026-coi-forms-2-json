"""Predefined pages from the Standardy (FR-09): applicant data, contact and consents, FINISH.

Sections come from templates.json, taken from references 5 and 1 with decisions K-05 (validation),
K-06 (TERYT_4G_DOWODOWY) and K-11 (MLPZ) applied. Code only picks the sections the applicant
kinds need, sets their visibility and gives every element a fresh id.
"""

import html
import json
import uuid
from collections.abc import Collection, Sequence
from importlib.resources import files

from forms2json.domain.form_definition import JsonObject, JsonValue, Question, State, Tab
from forms2json.domain.form_draft import ApplicantKind, Consent

# SHOW queries address pages by title, so these titles are part of the conditions.
APPLICANT_TAB = "Dane"
CONTACT_TAB = "Kontakt i zgody"
FINISH_TAB = "Strona końcowa"

FOR_WHOM = "wybierz_w_czyim_imieniu_wnioskujesz"
AS_WHOM = "wybierz_jako_kto_wnioskujesz"
SELF = "Swoim"
OTHER_PERSON = "Innej osoby"
LEGAL_ENTITY = "Osoby prawnej lub jednostki organizacyjnej"
# Standardy: a form addressed to an organ (e.g. "Do Wójta") gets the "Organ, do którego..." variant.
ORGAN_PREFIXES = ("wójt", "burmistrz", "prezydent", "starost", "marszał", "wojewod")

_TEMPLATES: dict[str, JsonObject] = json.loads(
    files("forms2json.domain.blocks").joinpath("templates.json").read_text(encoding="utf-8")
)


def applicant_page(addressee: str, kinds: Collection[ApplicantKind]) -> Tab:
    """First page: addressee, who applies, applicant data and the sections each kind needs."""
    # PROXY = acting for another person; the entity's proxy is a choice inside LEGAL_ENTITY.
    other = bool({ApplicantKind.OTHER_PERSON, ApplicantKind.PROXY} & set(kinds))
    entity = ApplicantKind.LEGAL_ENTITY in kinds
    for_other = _answer(FOR_WHOM, OTHER_PERSON)
    for_entity = _answer(FOR_WHOM, LEGAL_ENTITY)
    entity_proxy = f"{for_entity} and {_answer(AS_WHOM, 'Pełnomocnik')}"

    sections = [_office(addressee)]
    if other or entity:
        chosen = {SELF: ApplicantKind.SELF in kinds, OTHER_PERSON: other, LEGAL_ENTITY: entity}
        sections.append(_subject({name for name, on in chosen.items() if on}, entity))
    sections += [_section("twoje_dane"), _section("adres_zamieszkania")]
    if entity:
        sections += [
            _section("dane_podmiotu", for_entity),
            _section("adres_siedziby", for_entity),
            _section(
                "potwierdzenie_ze_jestes_reprezentantem",
                f"{for_entity} and {_answer(AS_WHOM, 'Reprezentant')}",
            ),
        ]
    if other:
        sections += [
            _section("dane_innej_osoby", for_other),
            _section("adres_zamieszkania_osoby_ktorej_jestes_pelnomocnikiem", for_other),
        ]
    if other or entity:
        proxy_cases = ([for_other] if other else []) + ([f"({entity_proxy})"] if entity else [])
        sections.append(_section("pelnomocnictwo", " or ".join(proxy_cases)))
    if other:
        sections.append(_section("oplata_skarbowa_pelnomocnictwo_1", for_other))
    if entity:
        sections.append(_section("oplata_skarbowa_pelnomocnictwo_2", entity_proxy))
    return _page(APPLICANT_TAB, "MAIN", sections)


def contact_page(consents: Sequence[Consent] = ()) -> Tab:
    """Second to last page: contact data and a CONSENT_SECTION; no consents = the GDPR clause."""
    consent = _section("zgoda_wyrazenie")
    if consents:
        items: list[JsonValue] = [
            {"description": _html(c.text), "required": c.required} for c in consents
        ]
        consent.field.repeating_section_grid[0].field.consent_section_config = {
            "consents": items,
            "files": [],
        }
        if len(consents) > 1:
            consent.field.title = "Zgody i oświadczenia"
    return _page(CONTACT_TAB, "MAIN", [_section("dane_do_kontaktu"), consent])


def finish_page() -> Tab:
    """FINISH page: a SECTION with the preview TEXT_BLOCK, as in the references (K-07)."""
    return _page(FINISH_TAB, "FINISH", [_section("podglad_uzupelnionego_wniosku")])


def _office(addressee: str) -> Question:
    is_organ = addressee.lower().removeprefix("do ").startswith(ORGAN_PREFIXES)
    office = _section(
        "organ_do_ktorego_jest_skladany_wniosek"
        if is_organ
        else "urzad_do_ktorego_jest_skladany_wniosek"
    )
    office.field.repeating_section_grid[0].field.default_value = addressee
    return office


def _subject(options: set[str], entity: bool) -> Question:
    subject = _section("podmiot_wniosku")
    for_whom = subject.field.repeating_section_grid[0].field
    for_whom.options = [o for o in for_whom.options if o.name in options]
    if not entity:  # "Pełnomocnik / Reprezentant" applies only to legal entities
        subject.field.repeating_section_grid = subject.field.repeating_section_grid[:1]
        subject.rows -= 1
    return subject


def _section(name: str, visible_when: str | None = None) -> Question:
    section = Question.from_dict(_TEMPLATES[name])
    section.field.id = str(uuid.uuid4())
    for child in section.field.repeating_section_grid:
        child.field.id = str(uuid.uuid4())
    if visible_when:
        section.field.states = [State("SHOW", visible_when)]
    return section


def _answer(field: str, option: str) -> str:
    return (
        f"(\"{option}\" in tabs['{APPLICANT_TAB}' in title]"
        f".questions['podmiot_wniosku' in field.techName]"
        f".field.repeatingSectionGrid['{field}' in field.techName].field.__userAnswer)"
    )


def _page(title: str, type_: str, sections: list[Question]) -> Tab:
    # shortcut: sections stacked by their template rows; real layout comes with #14.
    y = 0
    for section in sections:
        section.y = section.field.question_order = y
        y += section.rows
    return Tab(str(uuid.uuid4()), title, type_, sections)


def _html(text: str) -> str:
    return f"<html><head></head><body><p>{html.escape(text)}</p></body></html>"
