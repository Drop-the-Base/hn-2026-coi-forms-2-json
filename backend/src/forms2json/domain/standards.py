"""Design Standards (FR-09) and the official JSON schema (FR-06) checked on a form.

Standards checks are heuristics over labels and techNames, so they report WARNINGs;
a schema violation is an ERROR.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path

from forms2json.domain.form_definition import FormDefinition, JsonObject, JsonValue, Tab
from forms2json.domain.rules import Issue, Severity, _is_section, _walk
from forms2json.domain.validators import expected_validators

TITLE_PREFIXES = ("Wniosek", "Zgłoszenie", "Deklaracja", "Oświadczenie")
# techNames of the predefined blocks, as in the references (analiza §3).
OFFICE_SECTIONS = {
    "urzad_do_ktorego_jest_skladany_wniosek",
    "organ_do_ktorego_jest_skladany_wniosek",
}
PARTY_SECTIONS = OFFICE_SECTIONS | {"podmiot_wniosku", "twoje_dane"}
CONTACT_SECTION = "dane_do_kontaktu"
REQUIRED_SECTIONS = {
    "twoje_dane": "Twoje dane",
    CONTACT_SECTION: "Dane do kontaktu",
}
# Page stages from the Standards: parties → case → contact and consents → summary.
STAGES = ("strona postępowania", "sprawa", "kontakt i zgody", "podsumowanie")
CONSENT_LIKE = re.compile(r"zgod|zgadzam|oświadcz|oswiadcz", re.IGNORECASE)
CHOICE_TYPES = {"CHECKBOX", "RADIO"}
MAX_CHOICE_OPTIONS = 5
MAX_UNSEARCHABLE_OPTIONS = 15
# (pattern on title or techName, expected field type)
EXPECTED_TYPES = [
    (re.compile(r"^data\b|(^|_)data(_|$)", re.IGNORECASE), "DATEPICKER"),
    (re.compile(r"^(kwota|liczba)\b|(^|_)(kwota|liczba)(_|$)", re.IGNORECASE), "NUMBER"),
    (
        re.compile(r"^(uzasadnienie|opis)\b|(^|_)(uzasadnienie|opis)(_|$)", re.IGNORECASE),
        "TEXTAREA",
    ),
]
INFO_TYPES = {"TEXT_BLOCK", "INFO_SECTION", "CONSENT_SECTION"}
# A label holding a value from the document: postal code, street, blank to fill in.
VALUE_LIKE = re.compile(r"\b\d{2}-\d{3}\b|\b(ul|al)\.\s|…|\.{3}|_{3}", re.IGNORECASE)


def check_standards(form: FormDefinition) -> list[Issue]:
    return [
        *_check_title(form),
        *_check_page_order(form),
        *_check_predefined_sections(form),
        *_check_consents(form),
        *_check_field_types(form),
        *_check_field_labels(form),
    ]


def _warn(code: str, message: str, path: str) -> Issue:
    return Issue(code, message, path, Severity.WARNING)


def _check_title(form: FormDefinition) -> Iterator[Issue]:
    if form.title.strip() and not form.title.startswith(TITLE_PREFIXES):
        yield _warn(
            "S-TITLE",
            f"Tytuł „{form.title}” nie zaczyna się od: {', '.join(TITLE_PREFIXES)}.",
            "title",
        )


def _stage(tab: Tab) -> int:
    if tab.type == "FINISH":
        return 3
    fields = [q.field for q in tab.questions]
    nested = [q.field for f in fields for q in f.repeating_section_grid]
    if any(f.tech_name == CONTACT_SECTION for f in fields) or any(
        f.type == "CONSENT_SECTION" for f in fields + nested
    ):
        return 2
    if fields and fields[0].tech_name in PARTY_SECTIONS:
        return 0
    return 1


def _check_page_order(form: FormDefinition) -> Iterator[Issue]:
    # shortcut: a page's stage comes from known techNames; a case page that holds the contact
    # section looks like a contact page. Upgrade when blocks (#13) mark their stage.
    highest = 0
    for t, tab in enumerate(form.tabs):
        stage = _stage(tab)
        if stage < highest:
            yield _warn(
                "S-PAGE-ORDER",
                f"Strona „{tab.title}” ({STAGES[stage]}) stoi po stronie etapu "
                f"„{STAGES[highest]}”; kolejność to: {' → '.join(STAGES)}.",
                f"tabs[{t}]",
            )
        highest = max(highest, stage)


def _check_predefined_sections(form: FormDefinition) -> Iterator[Issue]:
    # shortcut: only the always-required blocks; conditional ones (Podmiot wniosku,
    # Pełnomocnictwo, Opłata skarbowa) depend on the source document, check them on FormDraft.
    placed = list(_walk(form))
    sections = {p.field.tech_name for p in placed if p.parent is None}
    if not sections & OFFICE_SECTIONS:
        yield _warn(
            "S-PREDEFINED",
            "Brak sekcji „Urząd, do którego jest składany wniosek” (albo „Organ, …”).",
            "tabs",
        )
    for tech_name, title in REQUIRED_SECTIONS.items():
        if tech_name not in sections:
            yield _warn("S-PREDEFINED", f"Brak sekcji predefiniowanej „{title}”.", "tabs")
    if not any(p.field.type == "CONSENT_SECTION" for p in placed):
        yield _warn("S-PREDEFINED", "Formularz nie ma sekcji zgód (CONSENT_SECTION).", "tabs")


def _check_consents(form: FormDefinition) -> Iterator[Issue]:
    for p in _walk(form):
        if p.field.type in CHOICE_TYPES and CONSENT_LIKE.search(
            f"{p.field.title} {p.field.tech_name}"
        ):
            yield _warn(
                "S-CONSENT",
                f"Pole „{p.field.tech_name}” wygląda na zgodę lub oświadczenie, a ma typ "
                f"{p.field.type}; zgody zbieramy w CONSENT_SECTION.",
                p.path,
            )


def _check_field_types(form: FormDefinition) -> Iterator[Issue]:
    for p in _walk(form):
        field = p.field
        if _is_section(field) or field.type in INFO_TYPES:
            continue
        name = field.tech_name
        labels = (field.title, name)
        for pattern, expected in EXPECTED_TYPES:
            if field.type != expected and any(pattern.search(label) for label in labels):
                yield _warn(
                    "S-FIELD-TYPE",
                    f"Pole „{name}” ma typ {field.type}, a jego etykieta wskazuje na {expected}.",
                    p.path,
                )
        for validator in expected_validators(field.title, name):
            if validator not in field.validation:
                yield _warn(
                    "S-VALIDATOR",
                    f"Pole „{name}” nie ma walidatora {validator}.",
                    f"{p.path}.validation",
                )
        if field.type in CHOICE_TYPES and len(field.options) > MAX_CHOICE_OPTIONS:
            yield _warn(
                "S-FIELD-TYPE",
                f"Pole „{name}” ma {len(field.options)} opcji; powyżej {MAX_CHOICE_OPTIONS} "
                "stosujemy listę rozwijaną (SELECT).",
                p.path,
            )
        if (
            field.type == "SELECT"
            and len(field.options) > MAX_UNSEARCHABLE_OPTIONS
            and not field.search_enabled
        ):
            yield _warn(
                "S-FIELD-TYPE",
                f"Lista „{name}” ma {len(field.options)} opcji i nie ma wyszukiwarki.",
                p.path,
            )


def _check_field_labels(form: FormDefinition) -> Iterator[Issue]:
    # Suspicious LLM fields lower the confidence (FR-T1) instead of passing at 0.9+.
    for p in _walk(form):
        title = p.field.title.strip()
        if not title or _is_section(p.field) or p.field.type in INFO_TYPES:
            continue
        if not any(ch.isalpha() for ch in title):
            yield _warn("S-FIELD-LABEL", f"Pole „{title}” nie ma etykiety.", p.path)
        elif title[0].islower():
            yield _warn(
                "S-FIELD-LABEL",
                f"Etykieta pola „{title}” zaczyna się małą literą: wygląda na tekst "
                "skopiowany z dokumentu, a nie na pytanie.",
                p.path,
            )
        if VALUE_LIKE.search(title):
            yield _warn(
                "S-FIELD-LABEL",
                f"Etykieta pola „{title}” wygląda na wartość z dokumentu, a nie na pytanie.",
                p.path,
            )


SCHEMA_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "boolean": bool,
}
SUPPORTED_KEYWORDS = {"$schema", "title", "type", "properties", "items"}


SCHEMA_PATH = Path(__file__).with_name("schema.json")


def read_schema() -> JsonObject:
    """The official schema exactly as published (served to the frontend by /form-schema)."""
    schema: JsonObject = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema


def load_schema() -> JsonObject:
    """The official schema with the K-09 typo fixed in our copy.

    The schema names the grid "repetingSectionGrid"; we generate "repeatingSectionGrid" like the
    references, so we rename the key before validating. Its items stay {} as in the original:
    nested fields are not checked by the schema, the R-rules walk them (K-09).
    """
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    schema: JsonObject = json.loads(text.replace('"repetingSectionGrid"', '"repeatingSectionGrid"'))
    return schema


def check_schema(data: JsonValue) -> list[Issue]:
    return list(_schema_issues(data, load_schema(), ""))


def _schema_issues(value: JsonValue, schema: JsonValue, path: str) -> Iterator[Issue]:
    # The official schema only uses type/properties/items (tested), so we check just those
    # instead of adding a JSON Schema library.
    assert isinstance(schema, dict)
    expected = schema.get("type")
    if isinstance(expected, str):
        ok = isinstance(value, SCHEMA_TYPES[expected]) and not (
            isinstance(value, bool) and expected == "number"
        )
        if not ok:
            yield Issue(
                "S-SCHEMA",
                f"Wartość „{path or '(dokument)'}” powinna mieć typ {expected} według schematu.",
                path,
            )
            return
    properties = schema.get("properties")
    if isinstance(value, dict) and isinstance(properties, dict):
        for key, sub in properties.items():
            if key in value:
                yield from _schema_issues(value[key], sub, f"{path}.{key}" if path else key)
    items = schema.get("items")
    if isinstance(value, list) and items is not None:
        for i, item in enumerate(value):
            yield from _schema_issues(item, items, f"{path}[{i}]")
