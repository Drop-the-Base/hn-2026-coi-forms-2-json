"""Deterministic FormDraft → FormDefinition (FR-07, FR-09, K-14).

Page order follows the Standardy and references 1 and 5: applicant data, the subject-matter page,
contact and consents, FINISH. Subject fields keep the document order, grouped by their section
in order of first appearance. The flow is linear (K-13).
"""

import html
from collections.abc import Iterator, Sequence
from itertools import pairwise

from forms2json.domain import rules
from forms2json.domain.blocks.pages import applicant_page, contact_page, finish_page
from forms2json.domain.draft_cleanup import SUBJECT_FALLBACK, clean_draft
from forms2json.domain.form_definition import Field, FlowLink, FormDefinition, Option, Question, Tab
from forms2json.domain.form_draft import DraftField, FieldType, FormDraft
from forms2json.domain.jsonata import answer_is, any_of, show
from forms2json.domain.layout import TechNames, layout_page, new_id, slugify
from forms2json.domain.validators import validation_for

ATTACHMENTS_SECTION = "Załączniki"
FEES_SECTION = "Opłaty"
PAYMENT_PROOF = "Potwierdzenie przelewu"
FEE_INFO = "oplata_info"
EMPTY_HTML = "<html><head></head><body></body></html>"

type Confidence = dict[str, float]


def compose(draft: FormDraft) -> tuple[FormDefinition, Confidence]:
    """The form plus the confidence of every page and field, keyed by JSON path like Issue.path.

    Elements of predefined blocks get 1.0 (FR-T1); the rest carry the draft's confidence.
    """
    draft = clean_draft(draft)
    applicant = applicant_page(draft.addressee.value, [a.kind for a in draft.applicants])
    contact = contact_page(draft.consents)
    finish = finish_page()
    names = TechNames(f.tech_name for tab in (applicant, contact, finish) for f in _walk(tab))
    subject, confidence = _subject_page(draft, names)
    tabs = [applicant, *subject, contact, finish]
    links = [FlowLink(new_id(), a.id, b.id) for a, b in pairwise(tabs)]
    if draft.consents:
        consent = next(f for f in _walk(contact) if f.type == "CONSENT_SECTION")
        confidence[consent.tech_name] = min(c.confidence for c in draft.consents)
    form = FormDefinition(draft.title.value, tabs, links)
    by_path = {f"tabs[{t}]": 1.0 for t in range(len(tabs))}
    by_path |= {p.path: confidence.get(p.field.tech_name, 1.0) for p in rules._walk(form)}
    return form, by_path


def _subject_page(draft: FormDraft, names: TechNames) -> tuple[list[Tab], Confidence]:
    grouped: dict[str, list[DraftField]] = {}
    for draft_field in draft.fields:
        grouped.setdefault(draft_field.section, []).append(draft_field)
    title = next(iter(grouped), SUBJECT_FALLBACK)

    confidence: Confidence = {}
    by_key: dict[str, tuple[str, Field]] = {}  # draft key -> (section techName, field)
    sections: list[Question] = []
    for section_title, draft_fields in grouped.items():
        section_name = names.new(section_title)  # before its fields: sections win name clashes
        children = []
        for f in draft_fields:
            field = _field(f.type, f.label, f.required, names, f.options)
            children.append(field)
            confidence[field.tech_name] = f.confidence
        sections.append(_section(section_title, section_name, children))
        for f, child in zip(draft_fields, children, strict=True):
            by_key[f.key] = (section_name, child)

    targets: dict[str, list[str]] = {}
    for c in draft.conditions:
        section_name, source = by_key[c.source]
        target = by_key[c.target][1]
        targets.setdefault(c.target, []).append(
            answer_is(c.value, title, section_name, source.tech_name)
        )
        confidence[target.tech_name] = min(confidence[target.tech_name], c.confidence)
    for key, queries in targets.items():
        by_key[key][1].states = [show(any_of(*queries))]

    if draft.attachments:
        attachments_name = names.new(ATTACHMENTS_SECTION)
        uploads = []
        for a in draft.attachments:
            upload = _field(FieldType.FILE_UPLOADER, a.name, a.required, names)
            uploads.append(upload)
            confidence[upload.tech_name] = a.confidence
        sections.append(_section(ATTACHMENTS_SECTION, attachments_name, uploads))
    if draft.fees:
        fees_name = names.new(FEES_SECTION)
        infos = []
        for fee in draft.fees:
            amount = "" if fee.amount is None else f": {fee.amount:.2f} zł".replace(".", ",")
            info = _field(FieldType.TEXT_BLOCK, FEE_INFO, False, names)
            info.title, info.description = "", _html(fee.description + amount)
            infos.append(info)
            confidence[info.tech_name] = fee.confidence
        # References pair the fee info with an upload of the transfer confirmation.
        proof = _field(FieldType.FILE_UPLOADER, PAYMENT_PROOF, True, names)
        sections.append(_section(FEES_SECTION, fees_name, [*infos, proof]))

    if not sections:
        return [], confidence
    layout_page(sections)
    return [Tab(new_id(), title, "MAIN", sections)], confidence


def _field(
    type_: str, label: str, required: bool, names: TechNames, options: Sequence[str] = ()
) -> Field:
    tech_name = names.new(label)
    return Field(
        id=new_id(),
        type=type_,
        tech_name=tech_name,
        title=label,
        question_order=0,
        options=[Option(o, o, slugify(o)) for o in options],
        validation=validation_for(label, tech_name, required),
        states=[],
    )


def _section(title: str, tech_name: str, children: list[Field]) -> Question:
    section = Field(
        id=new_id(),
        type="SECTION",
        tech_name=tech_name,
        title=title,
        question_order=0,
        description=EMPTY_HTML,
        repeating_section_grid=[Question(0, 0, 1, 1, child) for child in children],
        states=[],
    )
    return Question(0, 0, 1, 1, section)  # layout_page sets the real position


def _walk(tab: Tab) -> Iterator[Field]:
    for q in tab.questions:
        yield q.field
        yield from (child.field for child in q.field.repeating_section_grid)


def _html(text: str) -> str:
    return f"<html><head></head><body><p>{html.escape(text)}</p></body></html>"
