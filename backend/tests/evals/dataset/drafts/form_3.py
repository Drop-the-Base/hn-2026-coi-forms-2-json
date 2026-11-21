"""Golden JSON 3: Wniosek o wydanie zaświadczenia (UMiG Młynary). See ../README.md."""

from forms2json.domain.blocks.pages import CONTACT_TAB
from forms2json.domain.layout import layout_page
from tests.evals.dataset.drafts._common import build, field, html_text, rename_tab, save, tab

KIND = "Rodzaj zaświadczenia"
PURPOSE = "Cel wydania zaświadczenia"
OTHER = "Inne"

form = build(
    {
        "title": {"value": "Wniosek o wydanie zaświadczenia"},
        "addressee": {"value": "Urząd Miasta i Gminy Młynary"},
        # Paper asks only for a person (name, address, PESEL) -> self or another person.
        "applicants": [{"kind": "SELF"}, {"kind": "OTHER_PERSON"}],
        "fields": [
            {
                "key": "kind",
                "label": "Wybierz, czego ma dotyczyć zaświadczenie",
                "section": KIND,
                "type": "CHECKBOX",
                "required": True,
                "options": [
                    "Ilość posiadanych użytków rolnych w hektarach fizycznych i przeliczeniowych",
                    "Ilość dzierżawionych użytków rolnych w hektarach fizycznych "
                    "i przeliczeniowych",
                    "Okres posiadania gospodarstwa rolnego",
                    "Nieposiadanie użytków rolnych lub gospodarstwa rolnego "
                    "na terenie Gminy Młynary",
                    OTHER,
                ],
            },
            {
                "key": "other",
                "label": "Opisz, jakiego zaświadczenia potrzebujesz",
                "section": KIND,
                "type": "TEXTAREA",
                "required": True,
                "options": [],
            },
            {
                "key": "where",
                "label": "Gdzie przedstawisz zaświadczenie",
                "section": PURPOSE,
                "type": "TEXT_FIELD",
                "required": True,
                "options": [],
            },
        ],
        "conditions": [{"target": "other", "source": "kind", "value": OTHER}],
        "attachments": [],
        "fees": [{"description": "Opłata skarbowa", "amount": 17.0}],
        "consents": [],
    }
)

rename_tab(form, KIND, "Informacje o zaświadczeniu")
field(form, "opisz_jakiego_zaswiadczenia_potrzebujesz").tech_name = "inny_rodzaj_zaswiadczenia"
field(form, "gdzie_przedstawisz_zaswiadczenie").tech_name = "cel_wydania"

# Standardy: fees belong on the second to last page, next to contact data and consents.
subject, contact = tab(form, "Informacje o zaświadczeniu"), tab(form, CONTACT_TAB)
fee = next(q for q in subject.questions if q.field.title == "Opłaty")
subject.questions.remove(fee)
contact.questions.insert(1, fee)
layout_page(subject.questions)
layout_page(contact.questions)
fee.field.title, fee.field.tech_name = "Opłata skarbowa", "oplata_skarbowa"
info, proof = (q.field for q in fee.field.repeating_section_grid)
info.tech_name = "oplata_skarbowa_info"
info.description = html_text(
    "Opłata skarbowa za wydanie zaświadczenia wynosi 17 zł za każdy egzemplarz.",
    "Przelej ją przed złożeniem wniosku na konto Urzędu Miasta i Gminy Młynary: "
    "Bank PKO BP S.A. 12 1234 1234 1234 1234 1234 1234.",
    "Dodaj plik z potwierdzeniem przelewu. Znajdziesz go na stronie lub w aplikacji swojego banku.",
)
proof.title, proof.tech_name = "Plik z potwierdzeniem przelewu", "plik_z_potwierdzeniem_oplaty"
save(form, "3")
