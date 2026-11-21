"""Deterministic clean-up of the LLM draft before Compose (FR-07, FR-09, NFR-11).

A small model still copies paper artefacts as fields and page numbers as section names despite
the prompt. These generic checks know no specific form: they compare the draft with itself.
"""

import re

from forms2json.domain.form_draft import Applicant, ApplicantKind, DraftField, FormDraft, Text

SUBJECT_FALLBACK = "Informacje o wniosku"
PAGE_NAME = re.compile(r"^\s*strona\s+\d+\s*$", re.IGNORECASE)
# Paper-only elements the Standards drop: filing date and place, signature, stamp, and the
# headings of parts Compose builds from their own lists (attachments, fees, consents).
PAPER_LABEL = re.compile(
    r"^\W*(data(\s+(wniosku|złożenia|wypełnienia)\b.*)?|miejscowość(\W+i)?\W+data"
    r"|data(\W+i)?\W+miejscowość|(czytelny\s+)?podpis.*|piecz(ęć|ątka).*"
    r"|podstawa prawna|pouczenie|klauzula.*|załączniki|opłaty|zgody(\W+i\W+oświadczenia)?)\W*$",
    re.IGNORECASE,
)
# Applicant data come from predefined blocks (Standards), only the applicant kind is kept.
APPLICANT_DATA = re.compile(
    r"wnioskodawc.*(imię|nazwisk|nazwa|adres|pesel|nip|regon|telefon|mail)"
    r"|(imię|nazwisk|nazwa|adres|pesel|nip|regon|telefon|mail).*wnioskodawc",
    re.IGNORECASE,
)
# Personal or contact data with no owner but the applicant: blocks cover them.
BARE_PERSONAL = re.compile(
    r"^(\W|\s|i|lub|nr|numer|imię|imiona|nazwisko|nazwa|firmy|wnioskodawcy|adres|zamieszkania"
    r"|siedziba|siedziby|pesel|nip|regon|krs|telefonu?|tel|e-?mail|kontakt\w*)+$",
    re.IGNORECASE,
)
# A section naming someone else (another person, a child, an owner) keeps their data.
OTHER_OWNER = re.compile(r"osob|dzieck|dzieci|właściciel|członk|małżon", re.IGNORECASE)
ENTITY_DATA = re.compile(r"nazwa|firm|nip|regon|krs|siedzib", re.IGNORECASE)
# KPA art. 32: a party may always act through a proxy, so every e-service offers both.
ALWAYS_APPLICANTS = (ApplicantKind.SELF, ApplicantKind.PROXY)
INFERRED_CONFIDENCE = 0.5


def clean_draft(draft: FormDraft) -> FormDraft:
    """Drop paper, addressee and applicant-data fields; fix all-caps text and page-number sections.

    Applicant data name the applicant kinds instead: a name of a company means LEGAL_ENTITY.
    """
    addressee = f" {_norm(draft.addressee.value)} " if draft.addressee.value.strip() else ""
    applicant_data = [f for f in draft.fields if _is_applicant_data(f)]
    kinds = {a.kind for a in draft.applicants}
    added = [*ALWAYS_APPLICANTS]
    if any(ENTITY_DATA.search(f.label) for f in applicant_data):
        added.append(ApplicantKind.LEGAL_ENTITY)
    applicants = draft.applicants + [
        Applicant(kind=k, confidence=INFERRED_CONFIDENCE) for k in added if k not in kinds
    ]
    fields = [
        f.model_copy(
            update={
                "label": sentence_case(f.label),
                "section": SUBJECT_FALLBACK
                if PAGE_NAME.match(f.section) or not f.section.strip()
                else sentence_case(f.section),
            }
        )
        for f in draft.fields
        if f not in applicant_data and not _is_noise(f.label, addressee)
    ]
    keys = {f.key for f in fields}
    conditions = [c for c in draft.conditions if {c.source, c.target} <= keys]
    title = Text(value=sentence_case(draft.title.value), confidence=draft.title.confidence)
    update = {"title": title, "applicants": applicants, "fields": fields, "conditions": conditions}
    return draft.model_copy(update=update)


def sentence_case(text: str) -> str:
    """Shouted text in sentence case: an all-caps phrase, or all-caps words of 6+ letters.

    Short all-caps words (NIP, PESEL) are acronyms and mixed case is kept, so proper names survive.
    shortcut: proper names inside an all-caps phrase become lowercase, the text alone cannot tell
    them apart; the prompt asks the model for sentence case, this only catches what it misses.
    """
    words = text.split(" ")
    if len(text.split()) > 1 and text == text.upper():
        fixed = text.lower()
    else:
        fixed = " ".join(w.lower() if len(w) >= 6 and w == w.upper() else w for w in words)
    return text if fixed == text else fixed[:1].upper() + fixed[1:]


def _is_applicant_data(field: DraftField) -> bool:
    if APPLICANT_DATA.search(f"{field.section} {field.label}"):
        return True
    return bool(BARE_PERSONAL.match(field.label)) and not OTHER_OWNER.search(field.section)


def _is_noise(label: str, addressee: str) -> bool:
    norm = f" {_norm(label)} "
    return bool(PAPER_LABEL.match(label)) or (
        bool(addressee) and norm.strip() != "" and (norm in addressee or addressee in norm)
    )


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text).strip().casefold()
