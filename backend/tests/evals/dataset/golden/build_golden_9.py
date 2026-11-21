"""Builds 9.json (3 applications in 1, K-13): a hand-written draft through compose, then the parts
compose does not do: SHOW on whole sections, club sections moved to the applicant page, a
dictionary, validators outside validation_for and one consent section per variant.

Run from backend/: uv run python tests/evals/dataset/golden/build_golden_9.py
Ids are random, so every run rewrites the whole file; decisions: dataset/README.md, section 9.
"""

from pathlib import Path

from forms2json.domain import dictionaries
from forms2json.domain.blocks.pages import (
    APPLICANT_TAB,
    AS_WHOM,
    FOR_WHOM,
    LEGAL_ENTITY,
    contact_page,
)
from forms2json.domain.compose import compose
from forms2json.domain.form_definition import Field, JsonObject, Question, Tab
from forms2json.domain.form_draft import Consent, FormDraft
from forms2json.domain.jsonata import all_of, answer_is, any_of, show
from forms2json.domain.layout import layout_page

OUT = Path(__file__).with_name("9.json")
SUBJECT_TAB = "Informacje o wniosku"
SCHOLARSHIP, AWARD, DISTINCTION = "Stypendium sportowe", "Nagroda sportowa", "Wyróżnienie sportowe"
CLUB_CONTACT, CLUB_PROXY = "Dane kontaktowe klubu", "Dane pełnomocnika klubu"
POST, EPUAP, ADE = "Poczta tradycyjna", "Skrzynka ePUAP", "e-Doręczenia"
OTHER_ADDRESS = "Inny adres korespondencyjny"
PROCESSING = "w celu przekazania go do dalszego procedowania"
INFO_CLAUSE = (
    "Zapoznałem się z informacjami o ochronie danych osobowych. Podaje je administrator danych: "
    "klub sportowy (na swojej stronie internetowej lub w siedzibie) albo Prezydent Miasta Zgierza "
    "(w BIP Urzędu Miasta Zgierza: www.bip.zgierz.pl lub w siedzibie urzędu)."
)


def _f(label: str, section: str, type_: str, required: bool, *options: str) -> JsonObject:
    return {
        "key": label,
        "label": label,
        "section": section,
        "type": type_,
        "required": required,
        "options": list(options),
        "confidence": 1.0,
    }


# Document order (K-14); the two club sections go to the applicant page after compose.
FIELDS = [
    _f("Telefon kontaktowy klubu", CLUB_CONTACT, "TEXT_FIELD", False),
    _f("Sposób korespondencji z urzędem", CLUB_CONTACT, "RADIO", True, POST, EPUAP, ADE),
    _f(
        "Na który adres kierować korespondencję",
        CLUB_CONTACT,
        "RADIO",
        True,
        "Adres siedziby klubu",
        OTHER_ADDRESS,
    ),
    _f(OTHER_ADDRESS, CLUB_CONTACT, "TEXTAREA", True),
    _f("Adres skrzynki ePUAP", CLUB_CONTACT, "TEXT_FIELD", True),
    _f("Adres do e-Doręczeń", CLUB_CONTACT, "TEXT_FIELD", True),
    _f("Seria i numer dowodu osobistego", CLUB_PROXY, "TEXT_FIELD", True),
    _f("Odpis danych o klubie z KRS lub innego rejestru", CLUB_PROXY, "FILE_UPLOADER", True),
    _f("Wybierz rodzaj wniosku", "Rodzaj wniosku", "RADIO", True, SCHOLARSHIP, AWARD, DISTINCTION),
    _f("Imię", "Dane kandydata", "TEXT_FIELD", True),
    _f("Nazwisko", "Dane kandydata", "TEXT_FIELD", True),
    _f("Data urodzenia", "Dane kandydata", "DATEPICKER", True),
    _f("Adres zameldowania", "Dane kandydata", "TEXTAREA", True),
    _f("Adres do korespondencji", "Dane kandydata", "TEXTAREA", False),
    _f("Wybierz dyscypliny z listy", "Dyscypliny sportowe", "CHECKBOX", False),
    _f("Inna dyscyplina", "Dyscypliny sportowe", "TEXT_FIELD", False),
    _f("Najważniejsze osiągnięcia sportowe kandydata", "Osiągnięcia sportowe", "TEXTAREA", True),
    _f("Dyplomy lub inne dokumenty", "Osiągnięcia sportowe", "FILE_UPLOADER", False),
    _f(
        "Opinia klubu o postawie etycznej i moralnej kandydata",
        "Opinia macierzystego klubu sportowego",
        "TEXTAREA",
        True,
    ),
    _f("Dokument z opinią klubu", "Opinia macierzystego klubu sportowego", "FILE_UPLOADER", False),
    _f(
        "Dodatkowe informacje o kandydacie",
        "Dodatkowe informacje o osiągnięciach sportowych",
        "TEXTAREA",
        False,
    ),
    _f(
        "Imię i nazwisko zawodniczki lub zawodnika",
        "Dane podopiecznych trenera",
        "TEXT_FIELD",
        True,
    ),
    _f("Osiągnięcia sportowe podopiecznego", "Dane podopiecznych trenera", "TEXTAREA", True),
    _f(
        "Dokumenty potwierdzające osiągnięcia", "Dane podopiecznych trenera", "FILE_UPLOADER", False
    ),
    _f("Zaświadczenia o osiągnięciach sportowych", "Wymagane zaświadczenia", "FILE_UPLOADER", True),
]
DESCRIPTIONS = {
    "Dane kandydata": "W przypadku wyróżnienia sportowego kandydatem jest trener.",
    "Wymagane zaświadczenia": "Zaświadczenia wydane przez Polski Związek Sportowy właściwy dla "
    "dyscypliny lub inne oficjalne dokumenty (np. komunikaty z zawodów), które potwierdzają "
    "osiągnięcia sportowe kandydata, a przy wyróżnieniu: jego podopiecznych.",
}


def _consents(rules: str, committee: str, minor: bool, wards: bool) -> list[Consent]:
    who = "kandydat (a w przypadku kandydata nieletniego jego rodzic lub opiekun prawny)"
    if not minor:
        who = "kandydat"
    whos = [who]
    if wards:
        whos.append(
            "każdy podopieczny wskazany we wniosku (a w przypadku podopiecznego nieletniego "
            "jego rodzic lub opiekun prawny)"
        )
    texts = [INFO_CLAUSE]
    for w in whos:
        texts += [
            f"Oświadczam, że {w} wyraził zgodę na przetwarzanie danych osobowych zawartych we "
            f"wniosku {PROCESSING}{committee}.",
            f"Oświadczam, że {w} zapoznał się z regulaminem przyznawania {rules} Rady Miasta "
            "Zgierza i akceptuje wszystkie jego postanowienia.",
        ]
    return [Consent(text=t, required=True, confidence=1.0) for t in texts]


COMMITTEE = " przez Komisję stypendialną ds. stypendiów sportowych Rady Miasta Zgierza"
CONSENTS = {
    SCHOLARSHIP: _consents("stypendiów sportowych", COMMITTEE, minor=True, wards=False),
    AWARD: _consents("nagród sportowych", "", minor=True, wards=False),
    DISTINCTION: _consents("wyróżnień sportowych", "", minor=False, wards=True),
}


def _by_title(tab: Tab, title: str) -> Question:
    return next(q for q in tab.questions if q.field.title == title)


def _child(section: Question, title: str) -> Field:
    return next(c.field for c in section.field.repeating_section_grid if c.field.title == title)


def build() -> str:
    draft = FormDraft.from_dict(
        {
            "title": {
                "value": "Wniosek o przyznanie stypendium, nagrody lub wyróżnienia sportowego "
                "Rady Miasta Zgierza",
                "confidence": 1.0,
            },
            "addressee": {"value": "Urząd Miasta Zgierza", "confidence": 1.0},
            "applicants": [
                {"kind": "SELF", "confidence": 1.0},
                {"kind": "LEGAL_ENTITY", "confidence": 1.0},
            ],
            "fields": FIELDS,  # type: ignore[dict-item]
            "conditions": [],
            "attachments": [],
            "fees": [],
            "consents": [],
        }
    )
    form, _ = compose(draft)
    applicant, subject, contact, _finish = form.tabs
    subject.title = SUBJECT_TAB

    # Club contact and the proxy's ID card describe the applicant, so they join the club blocks.
    club_contact = _by_title(subject, CLUB_CONTACT)
    club_proxy = _by_title(subject, CLUB_PROXY)
    subject.questions.remove(club_contact)
    subject.questions.remove(club_proxy)
    names = [q.field.tech_name for q in applicant.questions]
    applicant.questions.insert(names.index("adres_siedziby") + 1, club_contact)
    names = [q.field.tech_name for q in applicant.questions]
    applicant.questions.insert(names.index("pelnomocnictwo"), club_proxy)

    club = answer_is(LEGAL_ENTITY, APPLICANT_TAB, "podmiot_wniosku", FOR_WHOM)
    proxy = all_of(club, answer_is("Pełnomocnik", APPLICANT_TAB, "podmiot_wniosku", AS_WHOM))
    club_contact.field.states = [show(club)]
    club_proxy.field.states = [show(proxy)]
    _child(club_proxy, "Seria i numer dowodu osobistego").validation.append("SERIAL_NUMBER_ID_CARD")

    contact_name = club_contact.field.tech_name
    channel = _child(club_contact, "Sposób korespondencji z urzędem").tech_name
    address = _child(club_contact, "Na który adres kierować korespondencję")

    def channel_is(value: str) -> str:
        return answer_is(value, APPLICANT_TAB, contact_name, channel)

    address.states = [show(channel_is(POST))]
    _child(club_contact, OTHER_ADDRESS).states = [
        show(
            all_of(
                channel_is(POST),
                answer_is(OTHER_ADDRESS, APPLICANT_TAB, contact_name, address.tech_name),
            )
        )
    ]
    for title, value, validator in (
        ("Adres skrzynki ePUAP", EPUAP, "EPUAP"),
        ("Adres do e-Doręczeń", ADE, "ADE"),
    ):
        box = _child(club_contact, title)
        box.states = [show(channel_is(value))]
        box.validation.append(validator)

    kind_section = _by_title(subject, "Rodzaj wniosku")
    kind = kind_section.field.repeating_section_grid[0].field.tech_name

    def kind_is(value: str) -> str:
        return answer_is(value, SUBJECT_TAB, kind_section.field.tech_name, kind)

    # compose names them imie_2 / nazwisko_2 (imie is taken by "Twoje dane"). Fails while
    # clean_draft drops a bare "Imię"/"Nazwisko" in "Dane kandydata" (#121), so 9.json is not
    # regenerated silently without the candidate's name.
    candidate = _by_title(subject, "Dane kandydata")
    _child(candidate, "Imię").tech_name = "imie_kandydata"
    _child(candidate, "Nazwisko").tech_name = "nazwisko_kandydata"

    disciplines = _by_title(subject, "Dyscypliny sportowe")
    disciplines.field.states = [show(kind_is(SCHOLARSHIP))]
    pick = _child(disciplines, "Wybierz dyscypliny z listy")
    dictionaries.use_dictionary(pick, dictionaries.SPORT_DISCIPLINES, [])
    pick.search_enabled = True
    pick.description = "Wybierz dyscypliny, w których startuje kandydat"
    _by_title(subject, "Osiągnięcia sportowe").field.states = [
        show(any_of(kind_is(SCHOLARSHIP), kind_is(AWARD)))
    ]
    wards = _by_title(subject, "Dane podopiecznych trenera")
    wards.field.type = "REPEATING_SECTION"  # paper has 4 fixed slots, the citizen adds as many
    wards.field.states = [show(kind_is(DISTINCTION))]
    for title, text in DESCRIPTIONS.items():
        _by_title(
            subject, title
        ).field.description = f"<html><head></head><body><p>{text}</p></body></html>"

    # One consent section per variant: texts differ in the rules' name and the consenting people.
    consent_sections = []
    for variant, consents in CONSENTS.items():
        section = contact_page(consents).questions[1]
        suffix = variant.lower().replace(" ", "_").replace("ó", "o").replace("ż", "z")
        section.field.tech_name = f"zgody_{suffix}"
        section.field.repeating_section_grid[0].field.tech_name = f"zgoda_{suffix}"
        section.field.title = f"Zgody i oświadczenia: {variant.lower()}"
        section.field.states = [show(kind_is(variant))]
        consent_sections.append(section)
    contact.questions = [contact.questions[0], *consent_sections]

    for tab in (applicant, subject, contact):
        layout_page(tab.questions)
    return form.to_json()


if __name__ == "__main__":
    OUT.write_text(build() + "\n", encoding="utf-8")
