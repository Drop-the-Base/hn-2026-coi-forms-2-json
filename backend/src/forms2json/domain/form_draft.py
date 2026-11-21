"""Intermediate model the LLM fills in the Understand step (FR-07, FR-T1).

Every element carries the confidence (0-1) the model reports for it. The LLM output is a
trust boundary, so `FormDraft.from_dict` validates it with pydantic before Compose sees it.
Pydantic is allowed in the domain only for this model (ADR-0020): the same class gives the
JSON Schema for structured output and the validation of the answer.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from forms2json.domain.form_definition import JsonObject


class InvalidFormDraft(ValueError):
    """Raised when the LLM output does not match the FormDraft schema."""


class ApplicantKind(StrEnum):
    SELF = "SELF"
    OTHER_PERSON = "OTHER_PERSON"
    LEGAL_ENTITY = "LEGAL_ENTITY"
    PROXY = "PROXY"


class FieldType(StrEnum):
    """Output field types (FormDefinition) a subject-matter field can map to.

    ADDRESS and PERSON are Standardy blocks, not output types: Compose expands them into an address
    section or Imię + Nazwisko, with the field's `key` as the techName suffix (whose data).
    """

    TEXT_FIELD = "TEXT_FIELD"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATEPICKER = "DATEPICKER"
    SELECT = "SELECT"
    RADIO = "RADIO"
    CHECKBOX = "CHECKBOX"
    FILE_UPLOADER = "FILE_UPLOADER"
    TEXT_BLOCK = "TEXT_BLOCK"
    ADDRESS = "ADDRESS"
    PERSON = "PERSON"


Confidence = Annotated[float, Field(ge=0, le=1)]


class _Strict(BaseModel):
    # No defaults anywhere and no extras: the subset strict structured output accepts.
    # strict=True stops pydantic coercing e.g. "17" or True into a number; enums opt out
    # because the LLM sends their values as plain strings.
    model_config = ConfigDict(extra="forbid", strict=True)


class Text(_Strict):
    value: str
    confidence: Confidence


class Applicant(_Strict):
    """Who may submit the application: on their own behalf, for another person, etc."""

    kind: Annotated[ApplicantKind, Field(strict=False)]
    confidence: Confidence


class DraftField(_Strict):
    """A field of the subject-matter part of the form, in document order (K-14)."""

    key: str
    label: str
    section: str
    type: Annotated[FieldType, Field(strict=False)]
    required: bool
    options: list[str]
    confidence: Confidence


class Condition(_Strict):
    """Field or attachment `target` is shown only when field `source` has answer `value`.

    Keys are not checked here: clean_draft drops a condition with an unknown key, so one bad
    reference costs that condition, not the whole form.
    """

    target: str
    source: str
    value: str
    confidence: Confidence


class Attachment(_Strict):
    key: str  # a condition target, in one namespace with field keys
    name: str
    required: bool
    confidence: Confidence


class Fee(_Strict):
    description: str
    amount: float | None  # PLN; None when the document names a fee without an amount
    confidence: Confidence


class Consent(_Strict):
    text: str
    required: bool
    confidence: Confidence


class FormDraft(_Strict):
    title: Text
    addressee: Text
    applicants: list[Applicant]
    fields: list[DraftField]
    conditions: list[Condition]
    attachments: list[Attachment]
    fees: list[Fee]
    consents: list[Consent]

    @classmethod
    def from_dict(cls, data: JsonObject) -> FormDraft:
        try:
            return cls.model_validate(data)
        except ValidationError as error:
            # Locations and messages only, no input values: the message reaches logs (NFR-06).
            errors = error.errors(include_url=False, include_input=False)
            details = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in errors)
            raise InvalidFormDraft(details) from error


FORM_DRAFT_SCHEMA: JsonObject = FormDraft.model_json_schema()
