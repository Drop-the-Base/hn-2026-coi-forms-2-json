"""Intermediate model the LLM fills in the Understand step (FR-07, FR-T1).

Every element carries the confidence (0-1) the model reports for it. The LLM output is a
trust boundary, so `FormDraft.from_dict` checks every type and range before Compose sees it.
"""

from dataclasses import asdict, dataclass
from enum import StrEnum

from forms2json.domain.form_definition import JsonObject, JsonValue


class InvalidFormDraft(ValueError):
    """Raised when the LLM output does not match the FormDraft schema."""


class ApplicantKind(StrEnum):
    SELF = "SELF"
    OTHER_PERSON = "OTHER_PERSON"
    LEGAL_ENTITY = "LEGAL_ENTITY"
    PROXY = "PROXY"


class FieldType(StrEnum):
    """Output field types (FormDefinition) a subject-matter field can map to."""

    TEXT_FIELD = "TEXT_FIELD"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATEPICKER = "DATEPICKER"
    SELECT = "SELECT"
    RADIO = "RADIO"
    CHECKBOX = "CHECKBOX"
    FILE_UPLOADER = "FILE_UPLOADER"
    TEXT_BLOCK = "TEXT_BLOCK"


@dataclass
class Text:
    value: str
    confidence: float

    @classmethod
    def from_dict(cls, data: JsonObject) -> Text:
        return cls(_str(data, "value"), _confidence(data))


@dataclass
class Applicant:
    """Who may submit the application: on their own behalf, for another person, etc."""

    kind: ApplicantKind
    confidence: float

    @classmethod
    def from_dict(cls, data: JsonObject) -> Applicant:
        return cls(_enum(ApplicantKind, data, "kind"), _confidence(data))


@dataclass
class DraftField:
    """A field of the subject-matter part of the form, in document order (K-14)."""

    key: str
    label: str
    section: str
    type: FieldType
    required: bool
    options: list[str]
    confidence: float

    @classmethod
    def from_dict(cls, data: JsonObject) -> DraftField:
        return cls(
            key=_str(data, "key"),
            label=_str(data, "label"),
            section=_str(data, "section"),
            type=_enum(FieldType, data, "type"),
            required=_bool(data, "required"),
            options=[_as_str(o, "options") for o in _list(data, "options")],
            confidence=_confidence(data),
        )


@dataclass
class Condition:
    """Field `target` is shown only when field `source` has answer `value`."""

    target: str
    source: str
    value: str
    confidence: float

    @classmethod
    def from_dict(cls, data: JsonObject) -> Condition:
        return cls(
            _str(data, "target"), _str(data, "source"), _str(data, "value"), _confidence(data)
        )


@dataclass
class Attachment:
    name: str
    required: bool
    confidence: float

    @classmethod
    def from_dict(cls, data: JsonObject) -> Attachment:
        return cls(_str(data, "name"), _bool(data, "required"), _confidence(data))


@dataclass
class Fee:
    description: str
    amount: float | None  # PLN; None when the document names a fee without an amount
    confidence: float

    @classmethod
    def from_dict(cls, data: JsonObject) -> Fee:
        amount = data.get("amount")
        return cls(
            _str(data, "description"),
            None if amount is None else _number(data, "amount"),
            _confidence(data),
        )


@dataclass
class Consent:
    text: str
    required: bool
    confidence: float

    @classmethod
    def from_dict(cls, data: JsonObject) -> Consent:
        return cls(_str(data, "text"), _bool(data, "required"), _confidence(data))


@dataclass
class FormDraft:
    title: Text
    addressee: Text
    applicants: list[Applicant]
    fields: list[DraftField]
    conditions: list[Condition]
    attachments: list[Attachment]
    fees: list[Fee]
    consents: list[Consent]

    def to_dict(self) -> JsonObject:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: JsonObject) -> FormDraft:
        draft = cls(
            title=Text.from_dict(_obj(data.get("title"))),
            addressee=Text.from_dict(_obj(data.get("addressee"))),
            applicants=[Applicant.from_dict(_obj(a)) for a in _list(data, "applicants")],
            fields=[DraftField.from_dict(_obj(f)) for f in _list(data, "fields")],
            conditions=[Condition.from_dict(_obj(c)) for c in _list(data, "conditions")],
            attachments=[Attachment.from_dict(_obj(a)) for a in _list(data, "attachments")],
            fees=[Fee.from_dict(_obj(f)) for f in _list(data, "fees")],
            consents=[Consent.from_dict(_obj(c)) for c in _list(data, "consents")],
        )
        _check_field_references(draft)
        return draft


def _check_field_references(draft: FormDraft) -> None:
    # Compose builds SHOW conditions by key, so a dangling or duplicate key breaks the form.
    keys = [f.key for f in draft.fields]
    if len(keys) != len(set(keys)):
        raise InvalidFormDraft("field keys must be unique")
    for condition in draft.conditions:
        for key in (condition.target, condition.source):
            if key not in keys:
                raise InvalidFormDraft(f"condition refers to unknown field '{key}'")


def _object(**properties: JsonValue) -> JsonObject:
    # Every property required and no extras: the subset strict structured output accepts.
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _array(items: JsonValue) -> JsonObject:
    return {"type": "array", "items": items}


def _enum_schema(values: type[StrEnum]) -> JsonObject:
    return {"type": "string", "enum": [v.value for v in values]}


_STRING: JsonObject = {"type": "string"}
_BOOLEAN: JsonObject = {"type": "boolean"}
_CONFIDENCE: JsonObject = {"type": "number", "minimum": 0, "maximum": 1}
_TEXT = _object(value=_STRING, confidence=_CONFIDENCE)

FORM_DRAFT_SCHEMA: JsonObject = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "FormDraft",
    **_object(
        title=_TEXT,
        addressee=_TEXT,
        applicants=_array(_object(kind=_enum_schema(ApplicantKind), confidence=_CONFIDENCE)),
        fields=_array(
            _object(
                key=_STRING,
                label=_STRING,
                section=_STRING,
                type=_enum_schema(FieldType),
                required=_BOOLEAN,
                options=_array(_STRING),
                confidence=_CONFIDENCE,
            )
        ),
        conditions=_array(
            _object(target=_STRING, source=_STRING, value=_STRING, confidence=_CONFIDENCE)
        ),
        attachments=_array(_object(name=_STRING, required=_BOOLEAN, confidence=_CONFIDENCE)),
        fees=_array(
            _object(
                description=_STRING,
                amount={"type": ["number", "null"]},
                confidence=_CONFIDENCE,
            )
        ),
        consents=_array(_object(text=_STRING, required=_BOOLEAN, confidence=_CONFIDENCE)),
    ),
}


def _obj(value: JsonValue) -> JsonObject:
    if not isinstance(value, dict):
        raise InvalidFormDraft(f"expected an object, got {type(value).__name__}")
    return value


def _list(data: JsonObject, key: str) -> list[JsonValue]:
    value = data.get(key)
    if not isinstance(value, list):
        raise InvalidFormDraft(f"'{key}' must be a list")
    return value


def _str(data: JsonObject, key: str) -> str:
    return _as_str(data.get(key), key)


def _as_str(value: JsonValue, key: str) -> str:
    if not isinstance(value, str):
        raise InvalidFormDraft(f"'{key}' must be a string")
    return value


def _bool(data: JsonObject, key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise InvalidFormDraft(f"'{key}' must be a boolean")
    return value


def _number(data: JsonObject, key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise InvalidFormDraft(f"'{key}' must be a number")
    return value


def _confidence(data: JsonObject) -> float:
    value = _number(data, "confidence")
    if not 0 <= value <= 1:
        raise InvalidFormDraft(f"'confidence' must be between 0 and 1, got {value}")
    return value


def _enum[E: StrEnum](enum: type[E], data: JsonObject, key: str) -> E:
    value = _str(data, key)
    try:
        return enum(value)
    except ValueError as error:
        raise InvalidFormDraft(f"'{key}' has unknown value '{value}'") from error
