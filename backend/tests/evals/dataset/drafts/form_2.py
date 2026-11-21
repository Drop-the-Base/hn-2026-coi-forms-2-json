"""Golden JSON 2: Wniosek o zwrot opłaty skarbowej (Urząd Gminy Stawiguda). See ../README.md."""

from tests.evals.dataset.drafts._common import build, field, html_text, save

CASE = "Informacje o opłacie skarbowej"
REASON = "Uzasadnienie wniosku"
REFUND = "Sposób zwrotu opłaty"
TRANSFER = "Przelewem na rachunek bankowy"

form = build(
    {
        "title": {"value": "Wniosek o zwrot opłaty skarbowej"},
        "addressee": {"value": "Urząd Gminy Stawiguda"},
        # Paper: "Nazwa / Imię i nazwisko" + NIP and a proxy -> person, other person and entity.
        "applicants": [{"kind": "SELF"}, {"kind": "OTHER_PERSON"}, {"kind": "LEGAL_ENTITY"}],
        "fields": [
            {
                "key": "date",
                "label": "Data uiszczenia opłaty",
                "section": CASE,
                "type": "DATEPICKER",
                "required": True,
                "options": [],
            },
            {
                "key": "amount",
                "label": "Kwota opłaty",
                "section": CASE,
                "type": "NUMBER",
                "required": True,
                "options": [],
            },
            {
                "key": "organ",
                "label": "Nazwa organu, w którym zapłacono opłatę",
                "section": CASE,
                "type": "TEXT_FIELD",
                "required": True,
                "options": [],
            },
            {
                "key": "reason",
                "label": "Uzasadnienie",
                "section": REASON,
                "type": "TEXTAREA",
                "required": True,
                "options": [],
            },
            {
                "key": "refund",
                "label": "Wybierz sposób zwrotu opłaty",
                "section": REFUND,
                "type": "RADIO",
                "required": True,
                "options": ["Gotówką w kasie urzędu", TRANSFER],
            },
            {
                "key": "account",
                "label": "Numer rachunku",
                "section": REFUND,
                "type": "TEXT_FIELD",
                "required": True,
                "options": [],
            },
            {
                "key": "owner",
                "label": "Imię i nazwisko lub nazwa właściciela rachunku",
                "section": REFUND,
                "type": "TEXT_FIELD",
                "required": True,
                "options": [],
            },
        ],
        "conditions": [
            {"target": "account", "source": "refund", "value": TRANSFER},
            {"target": "owner", "source": "refund", "value": TRANSFER},
        ],
        # Paper attachments (pełnomocnictwo, opłata za nie) are the predefined proxy blocks.
        "attachments": [],
        "fees": [],
        "consents": [],
    }
)

field(form, "uzasadnienie").description = html_text(
    "Opisz, dlaczego opłata skarbowa, której dotyczy wniosek, została zapłacona błędnie."
)
field(form, "imie_i_nazwisko_lub_nazwa_wlasciciela_rachunku").tech_name = "wlasciciel_rachunku"
save(form, "2")
