"""Technical form rules (FR-08) checked on a FormDefinition; each violation becomes an Issue."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from forms2json.domain.form_definition import Field, FormDefinition, Question, Tab

MAX_TITLE_LENGTH = 255
SECTION_TYPES = {"SECTION", "REPEATING_SECTION"}
# Rules allow only INFO_SECTION on FINISH; the references use TEXT_BLOCK, so both pass (K-07).
FINISH_FIELD_TYPES = {"TEXT_BLOCK", "INFO_SECTION"}
VALIDATORS = {
    "REQUIRED",
    "EMAIL",
    "PESEL",
    "NIP",
    "REGON",
    "ZIP_CODE",
    "EPUAP",
    "ADE",
    "SERIAL_NUMBER_ID_CARD",
}
SECTION_STATES = {"SHOW"}
FIELD_STATES = {"SHOW", "READ_ONLY"}
TECH_NAME_REF = re.compile(r"'([^']+)'\s*in\s+(?:field\.techName|fieldTechName)")
TAB_TITLE_REF = re.compile(r"'([^']+)'\s*in\s+title")


class Severity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    path: str
    severity: Severity = Severity.ERROR


@dataclass(frozen=True)
class _Placed:
    """A field found by the recursive walk, with the section it sits in (None = page level)."""

    tab: Tab
    field: Field
    parent: Field | None
    path: str


def check_rules(form: FormDefinition) -> list[Issue]:
    placed = list(_walk(form))
    return [
        *_check_title(form),
        *_check_tab_types(form),
        *_check_fields_per_tab(form, placed),
        *_check_nesting(placed),
        *_check_finish_fields(placed),
        *_check_obligatoriness(placed),
        *_check_flow(form),
        *_check_states(form, placed),
    ]


def _walk(form: FormDefinition) -> Iterator[_Placed]:
    # Descend into every grid ourselves: the official schema checks no field (K-09).
    def descend(
        tab: Tab, questions: list[Question], parent: Field | None, path: str
    ) -> Iterator[_Placed]:
        for i, question in enumerate(questions):
            here = f"{path}[{i}].field"
            yield _Placed(tab, question.field, parent, here)
            yield from descend(
                tab,
                question.field.repeating_section_grid,
                question.field,
                f"{here}.repeatingSectionGrid",
            )

    for t, tab in enumerate(form.tabs):
        yield from descend(tab, tab.questions, None, f"tabs[{t}].questions")


def _is_section(field: Field) -> bool:
    return field.type in SECTION_TYPES


def _is_finish(tab: Tab) -> bool:
    return tab.type == "FINISH"


def _check_title(form: FormDefinition) -> Iterator[Issue]:
    if not form.title.strip():
        yield Issue("R-TITLE", "Formularz nie ma tytułu.", "title")
    elif len(form.title) > MAX_TITLE_LENGTH:
        yield Issue(
            "R-TITLE",
            f"Tytuł formularza ma {len(form.title)} znaków, dozwolone jest {MAX_TITLE_LENGTH}.",
            "title",
        )


def _check_tab_types(form: FormDefinition) -> Iterator[Issue]:
    if len(form.tabs) < 2:
        yield Issue(
            "R-TAB-COUNT",
            f"Formularz ma {len(form.tabs)} stron, wymagane są co najmniej 2.",
            "tabs",
        )
    for t, tab in enumerate(form.tabs):
        expected = "FINISH" if t == len(form.tabs) - 1 else "MAIN"
        if tab.type != expected:
            yield Issue(
                "R-TAB-TYPE",
                f"Strona „{tab.title}” ma typ {tab.type}, a powinna mieć {expected}.",
                f"tabs[{t}]",
            )


def _check_fields_per_tab(form: FormDefinition, placed: list[_Placed]) -> Iterator[Issue]:
    tabs_with_fields = {id(p.tab) for p in placed if not _is_section(p.field)}
    for t, tab in enumerate(form.tabs):
        if id(tab) not in tabs_with_fields:
            yield Issue("R-TAB-EMPTY", f"Strona „{tab.title}” nie ma żadnego pola.", f"tabs[{t}]")


def _check_nesting(placed: list[_Placed]) -> Iterator[Issue]:
    for p in placed:
        name = p.field.tech_name
        if _is_section(p.field):
            if p.parent is not None:
                yield Issue(
                    "R-SECTION-NESTED",
                    f"Sekcja „{name}” jest zagnieżdżona w „{p.parent.tech_name}”.",
                    p.path,
                )
        elif p.parent is None or not _is_section(p.parent):
            # The rules' variant of K-07: INFO_SECTION placed directly on the FINISH page.
            if p.parent is None and _is_finish(p.tab) and p.field.type == "INFO_SECTION":
                continue
            yield Issue("R-FIELD-OUTSIDE-SECTION", f"Pole „{name}” nie leży w sekcji.", p.path)


def _check_finish_fields(placed: list[_Placed]) -> Iterator[Issue]:
    for p in placed:
        if (
            _is_finish(p.tab)
            and not _is_section(p.field)
            and p.field.type not in FINISH_FIELD_TYPES
        ):
            yield Issue(
                "R-FINISH-INPUT",
                f"Na stronie końcowej jest pole „{p.field.tech_name}” typu {p.field.type}; "
                "dozwolone są tylko TEXT_BLOCK i INFO_SECTION.",
                p.path,
            )


def _check_obligatoriness(placed: list[_Placed]) -> Iterator[Issue]:
    # K-05: `validation` is the obligatoriness attribute ([] optional, ["REQUIRED", ...] required);
    # the model already rejects a missing key and reads the references' {} as [].
    for p in placed:
        unknown = [v for v in p.field.validation if v not in VALIDATORS]
        if unknown:
            yield Issue(
                "R-OBLIGATORY",
                f"Pole „{p.field.tech_name}” ma nieznane walidatory: {', '.join(unknown)}.",
                f"{p.path}.validation",
            )
        if p.field.type == "CONSENT_SECTION" and not _consents_have_required(p.field):
            yield Issue(
                "R-OBLIGATORY",
                f"Sekcja zgód „{p.field.tech_name}” ma zgodę bez atrybutu „required”.",
                f"{p.path}.consentSectionConfig",
            )


def _consents_have_required(field: Field) -> bool:
    consents = (field.consent_section_config or {}).get("consents")
    if not isinstance(consents, list) or not consents:
        return False
    return all(isinstance(c, dict) and isinstance(c.get("required"), bool) for c in consents)


def _check_flow(form: FormDefinition) -> Iterator[Issue]:
    tab_ids = {tab.id for tab in form.tabs}
    next_tabs: dict[str, set[str]] = {}
    for i, link in enumerate(form.links):
        for end in (link.source, link.target):
            if end not in tab_ids:
                yield Issue(
                    "R-FLOW",
                    f"Przejście „{link.id}” wskazuje nieistniejącą stronę {end}.",
                    f"flow.links[{i}]",
                )
        next_tabs.setdefault(link.source, set()).add(link.target)
    if not form.tabs:
        return
    reached = {form.tabs[0].id}
    frontier = [form.tabs[0].id]
    while frontier:
        for target in next_tabs.get(frontier.pop(), set()) - reached:
            reached.add(target)
            frontier.append(target)
    for t, tab in enumerate(form.tabs):
        if tab.id not in reached:
            yield Issue(
                "R-FLOW",
                f"Do strony „{tab.title}” nie prowadzi żadne przejście z pierwszej strony.",
                f"tabs[{t}]",
            )


def _check_states(form: FormDefinition, placed: list[_Placed]) -> Iterator[Issue]:
    # shortcut: a dependency without any state is invisible in the JSON, so we check the states
    # that exist; detecting missing ones needs the source document (FormDraft).
    tech_names = {p.field.tech_name for p in placed}
    tab_titles = {tab.title for tab in form.tabs}
    for p in placed:
        allowed = SECTION_STATES if _is_section(p.field) else FIELD_STATES
        for s, state in enumerate(p.field.states or []):
            path = f"{p.path}.states[{s}]"
            name = p.field.tech_name
            if state.type not in allowed:
                yield Issue(
                    "R-STATES", f"Element „{name}” ma niedozwolony stan {state.type}.", path
                )
            if not state.query.strip():
                yield Issue(
                    "R-STATES", f"Stan {state.type} elementu „{name}” nie ma warunku JSONata.", path
                )
            for ref in sorted(set(TECH_NAME_REF.findall(state.query)) - tech_names):
                yield Issue(
                    "R-STATES",
                    f"Warunek elementu „{name}” odwołuje się do nieistniejącego pola „{ref}”.",
                    path,
                    Severity.WARNING,
                )
            for ref in sorted(set(TAB_TITLE_REF.findall(state.query)) - tab_titles):
                yield Issue(
                    "R-STATES",
                    f"Warunek elementu „{name}” odwołuje się do nieistniejącej strony „{ref}”.",
                    path,
                    Severity.WARNING,
                )
