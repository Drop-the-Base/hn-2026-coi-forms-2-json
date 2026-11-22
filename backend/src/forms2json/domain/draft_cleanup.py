"""Deterministic clean-up of the LLM draft before Compose (FR-07, FR-09, NFR-11).

A small model still copies paper artefacts as fields and page numbers as section names despite
the prompt. These generic checks know no specific form: they compare the draft with itself.
"""

import re
from itertools import groupby

from forms2json.domain.form_draft import (
    Applicant,
    ApplicantKind,
    Attachment,
    Condition,
    DraftField,
    FieldType,
    FormDraft,
    Text,
)
from forms2json.domain.layout import slugify

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
    r"^(\W|\s|i|lub|nr|numer|imię|imiona|nazwisko|nazwa|pełna|firmy|podmiotu|wnioskodawcy|adres"
    r"|zamieszkania|siedziba|siedziby|pesel|nip|regon|krs|telefonu?|tel|fax|e\W?mail|kontakt\w*"
    r"|dot|tylko|osób|prawnych)+$",
    re.IGNORECASE,
)
# A section naming someone else (another person, a child, an owner) keeps their data.
OTHER_OWNER = re.compile(r"osob|dzieck|dzieci|właściciel|członk|małżon", re.IGNORECASE)
# A paper position number in a label ("(suma poz. 38 i 41)"): the e-service has no positions.
POSITION_REF = re.compile(r"\s*\([^)]*\bpoz\w*\.?\s*\d[^)]*\)", re.IGNORECASE)
ATTACHMENTS_SECTION = re.compile(r"\bzałącznik", re.IGNORECASE)
# The applicant page of the Standardy has the power of attorney upload and its stamp duty.
PROXY = re.compile(r"pełnomoc", re.IGNORECASE)
# A correspondence address is filled in only when it differs: the e-service asks first (golden 8).
CORRESPONDENCE = re.compile(r"korespondenc", re.IGNORECASE)
CORRESPONDENCE_GATE = "Czy adres do korespondencji jest inny niż adres zamieszkania lub siedziby?"
YES, NO = "Tak", "Nie"
# Parts the e-service ADDRESS block already has: 3+ in one section are one address, and next to
# an ADDRESS field even one is a repeat.
ADDRESS_PART = re.compile(
    r"^(kraj|województwo|powiat|gmina|miejscowość|poczta|kod pocztowy|ulica"
    r"|(nr|numer) (nieruchomości|domu|lokalu|budynku))\b",
    re.IGNORECASE,
)
MIN_ADDRESS_PARTS = 3
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
    attachments = [a for a in draft.attachments if not PROXY.search(a.name)]
    listed = [f for f in draft.fields if _is_listed_attachment(f)]
    for f in listed:  # attachments given as fields belong to the attachment list
        if not PROXY.search(f.label) and not any(_same(f.label, a.name) for a in attachments):
            attachments.append(Attachment(name=f.label, required=False, confidence=f.confidence))
    fields = [
        f.model_copy(
            update={
                "label": sentence_case(POSITION_REF.sub("", f.label).strip()),
                "section": SUBJECT_FALLBACK
                if PAGE_NAME.match(f.section) or not f.section.strip()
                else sentence_case(f.section),
            }
        )
        for f in draft.fields
        if f not in applicant_data
        and f not in listed
        and not any(_same(f.label, c.text) for c in draft.consents)  # the contact page has them
        and not _is_noise(f.label, addressee)
    ]
    fields, conditions = _collapse_addresses(fields, list(draft.conditions))
    keys = {f.key for f in fields}
    conditions = [c for c in conditions if {c.source, c.target} <= keys]
    fields, conditions = _correspondence_gates(fields, conditions)
    title = Text(value=sentence_case(draft.title.value), confidence=draft.title.confidence)
    fees = [fee for fee in draft.fees if not PROXY.search(fee.description)]
    update = {
        "title": title,
        "applicants": applicants,
        "fields": fields,
        "conditions": conditions,
        "attachments": attachments,
        "fees": fees,
    }
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


def _collapse_addresses(
    fields: list[DraftField], conditions: list[Condition]
) -> tuple[list[DraftField], list[Condition]]:
    """Address parts (Kraj, Ulica, Kod pocztowy...) spelled out as fields become one ADDRESS field
    per section, or go when the section already has one; conditions on a part move to it."""
    out: list[DraftField] = []
    moved: dict[str, str] = {}
    for section, group in groupby(fields, key=lambda f: f.section):
        items = list(group)
        parts = [
            f for f in items if f.type is not FieldType.ADDRESS and ADDRESS_PART.match(f.label)
        ]
        address = next((f for f in items if f.type is FieldType.ADDRESS), None)
        if not parts or (address is None and len(parts) < MIN_ADDRESS_PARTS):
            out += items
            continue
        kept = [f for f in items if f not in parts]
        if address is None:
            label = section if section.lower().startswith("adres") else f"Adres ({section.lower()})"
            key = slugify(label).removeprefix("adres_") or "adres"
            address = parts[0].model_copy(
                update={"key": key, "label": label, "type": FieldType.ADDRESS, "options": []}
            )
            kept.insert(items.index(parts[0]), address)  # nothing before the first part was dropped
        moved |= {f.key: address.key for f in parts}
        out += kept
    conditions = [
        c.model_copy(update={"target": moved.get(c.target, c.target)}) for c in conditions
    ]
    return out, conditions


def _correspondence_gates(
    fields: list[DraftField], conditions: list[Condition]
) -> tuple[list[DraftField], list[Condition]]:
    """A Tak/Nie question before each correspondence address that nothing else shows or hides."""
    targets = {c.target for c in conditions}
    keys = {f.key for f in fields}
    out: list[DraftField] = []
    for f in fields:
        if f.type is FieldType.ADDRESS and CORRESPONDENCE.search(f.label) and f.key not in targets:
            gate = f"{f.key}_inny"
            while gate in keys:
                gate += "_"
            keys.add(gate)
            out.append(
                f.model_copy(
                    update={
                        "key": gate,
                        "label": CORRESPONDENCE_GATE,
                        "type": FieldType.RADIO,
                        "required": True,
                        "options": [YES, NO],
                    }
                )
            )
            conditions = [
                *conditions,
                Condition(target=f.key, source=gate, value=YES, confidence=f.confidence),
            ]
        out.append(f)
    return out, conditions


def _is_listed_attachment(field: DraftField) -> bool:
    """A field of an attachments section: the attachment list (uploads) covers it."""
    return bool(ATTACHMENTS_SECTION.search(field.section)) and field.type in {
        FieldType.CHECKBOX,
        FieldType.RADIO,
        FieldType.FILE_UPLOADER,
        FieldType.TEXT_FIELD,
        FieldType.TEXTAREA,
    }


def _same(a: str, b: str) -> bool:
    """'Inne (podać jakie)' and 'Inne załączniki': one name, without remarks, starts the other."""
    x, y = (_norm(re.sub(r"\(.*?\)", "", t)) for t in (a, b))
    return bool(x and y) and (x.startswith(y) or y.startswith(x))


def _is_noise(label: str, addressee: str) -> bool:
    norm = f" {_norm(label)} "
    return bool(PAPER_LABEL.match(label)) or (
        bool(addressee) and norm.strip() != "" and (norm in addressee or addressee in norm)
    )


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text).strip().casefold()
