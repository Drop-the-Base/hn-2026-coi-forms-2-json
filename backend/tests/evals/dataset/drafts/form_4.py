"""Golden JSON 4: Wniosek o wynajęcie lub użyczenie świetlicy wiejskiej. See ../README.md."""

from forms2json.domain.blocks.pages import contact_page
from forms2json.domain.form_definition import JsonObject
from tests.evals.dataset.drafts._common import build, field, fields, html_text, save

BOOKING = "Rezerwacja świetlicy"
EVENT = "Informacje o wydarzeniu"
RESPONSIBLE = "Osoba odpowiedzialna za porządek i bezpieczeństwo"
SOMEONE_ELSE = "Inna osoba"


def _text(key: str, label: str, section: str, type_: str = "TEXT_FIELD") -> JsonObject:
    return {
        "key": key,
        "label": label,
        "section": section,
        "type": type_,
        "required": True,
        "options": [],
    }


form = build(
    {
        "title": {"value": "Wniosek o wynajęcie lub użyczenie świetlicy wiejskiej"},
        "addressee": {"value": "Wójt Gminy Płoskinia"},
        # Paper asks only for a person (name, address, phone) -> self or another person.
        "applicants": [{"kind": "SELF"}, {"kind": "OTHER_PERSON"}],
        "fields": [
            {
                **_text("kind", "Wybierz, czego dotyczy wniosek", BOOKING, "RADIO"),
                "options": ["Wynajęcie", "Użyczenie"],
            },
            _text("village", "Miejscowość, w której jest świetlica", BOOKING),
            _text("from", "Data rozpoczęcia", BOOKING, "DATEPICKER"),
            _text("to", "Data zakończenia", BOOKING, "DATEPICKER"),
            _text("purpose", "Cel wynajęcia świetlicy", EVENT),
            _text("people", "Przewidywana liczba uczestników", EVENT, "NUMBER"),
            {
                **_text("who", "Kto odpowiada za porządek i bezpieczeństwo?", RESPONSIBLE, "RADIO"),
                "options": ["Ja", SOMEONE_ELSE],
            },
            _text("name", "Imię", RESPONSIBLE),
            _text("surname", "Nazwisko", RESPONSIBLE),
            _text(
                "consent",
                "Plik ze zgodą i oświadczeniem osoby odpowiedzialnej",
                RESPONSIBLE,
                "FILE_UPLOADER",
            ),
        ],
        "conditions": [
            {"target": key, "source": "who", "value": SOMEONE_ELSE}
            for key in ("name", "surname", "consent")
        ],
        "attachments": [],
        "fees": [],
        "consents": [
            {"text": text, "required": True}
            for text in (
                "Znam warunki wynajmu świetlicy wiejskiej.",
                "W czasie wynajmu odpowiadam za ład i porządek w świetlicy "
                "oraz na terenie przy świetlicy.",
                "W czasie wydarzenia przestrzegam przepisów sanitarnych, BHP i przeciwpożarowych.",
                "W czasie wynajmu ponoszę pełną odpowiedzialność za powierzone mienie.",
            )
        ],
    }
)

# compose suffixed the clashing labels; give them the context suffix the references use.
names = {
    "kto_odpowiada_za_porzadek_i_bezpieczenstwo": "osoba_odpowiedzialna",
    "imie_2": "imie_osoba_odpowiedzialna",
    "nazwisko_2": "nazwisko_osoba_odpowiedzialna",
    "plik_ze_zgoda_i_oswiadczeniem_osoby_odpowiedzialnej": "zgoda_osoby_odpowiedzialnej",
}
for f in fields(form):
    f.tech_name = names.get(f.tech_name, f.tech_name)
    for state in f.states or []:
        for old, new in names.items():
            state.query = state.query.replace(f"'{old}'", f"'{new}'")

field(form, "osoba_odpowiedzialna_za_porzadek_i_bezpieczenstwo").description = html_text(
    "Osoba odpowiedzialna musi być pełnoletnia. Jeśli to nie Ty, dodaj jej zgodę "
    "i podpisane przez nią oświadczenia, takie jak w sekcji „Zgody i oświadczenia”."
)
field(form, "cel_wynajecia_swietlicy").description = html_text(
    "Rodzaj uroczystości, np. wesele, urodziny, zabawa."
)
# Statements come on top of the GDPR consent the Standardy require on every form.
consent = field(form, "zgoda").consent_section_config
gdpr = contact_page().questions[1].field.repeating_section_grid[0].field
assert consent is not None and gdpr.consent_section_config is not None
statements, clause = consent["consents"], gdpr.consent_section_config["consents"]
assert isinstance(statements, list) and isinstance(clause, list)
consent["consents"] = [*statements, *clause]
save(form, "4")
