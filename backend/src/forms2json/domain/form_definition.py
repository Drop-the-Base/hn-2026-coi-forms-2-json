"""Output model of a form configuration, shaped like the reference JSONs (FR-06)."""

import json
from dataclasses import dataclass, field

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None
type JsonObject = dict[str, JsonValue]


class InvalidFormDefinition(ValueError):
    """Raised when a JSON document does not have the reference form structure."""


@dataclass
class Option:
    id: str
    name: str
    tech_name: str | None = None

    def to_dict(self) -> JsonObject:
        return _drop_none({"id": self.id, "name": self.name, "techName": self.tech_name})

    @classmethod
    def from_dict(cls, data: JsonObject) -> Option:
        return cls(_str(data, "id"), _str(data, "name"), _opt_str(data, "techName"))


@dataclass
class State:
    """Conditional field state, e.g. SHOW or READ_ONLY driven by a JSONata query."""

    type: str
    query: str

    def to_dict(self) -> JsonObject:
        return {"type": self.type, "query": self.query}

    @classmethod
    def from_dict(cls, data: JsonObject) -> State:
        return cls(_str(data, "type"), _str(data, "query"))


@dataclass
class Field:
    id: str
    type: str
    tech_name: str
    title: str
    question_order: int
    description: str = ""
    tooltip_message: str = ""
    read_only: bool = False
    options: list[Option] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    # Reference JSONs use repeatingSectionGrid; the schema's "repetingSectionGrid" is a typo (K-09).
    repeating_section_grid: list[Question] = field(default_factory=list)
    # None means the key is absent; one field in the references has no "states" at all.
    states: list[State] | None = None
    default_value: str | list[str] | None = None
    default_value_type: str | None = None
    dictionary_name: str | None = None
    multi_level_tree: bool | None = None
    search_enabled: bool | None = None
    # shortcut: kept as raw JSON, model it when a pipeline step needs to build consents.
    consent_section_config: JsonObject | None = None

    def to_dict(self) -> JsonObject:
        return _drop_none(
            {
                "id": self.id,
                "type": self.type,
                "techName": self.tech_name,
                "title": self.title,
                "description": self.description,
                "options": [o.to_dict() for o in self.options],
                "validation": list(self.validation),
                "readOnly": self.read_only,
                "repeatingSectionGrid": [q.to_dict() for q in self.repeating_section_grid],
                "defaultValue": _default_value_json(self.default_value),
                "defaultValueType": self.default_value_type,
                "dictionaryName": self.dictionary_name,
                "multiLevelTree": self.multi_level_tree,
                "searchEnabled": self.search_enabled,
                "consentSectionConfig": self.consent_section_config,
                "states": None if self.states is None else [s.to_dict() for s in self.states],
                "questionOrder": self.question_order,
                "tooltipMessage": self.tooltip_message,
            }
        )

    @classmethod
    def from_dict(cls, data: JsonObject) -> Field:
        states = data.get("states")
        consent = data.get("consentSectionConfig")
        return cls(
            id=_str(data, "id"),
            type=_str(data, "type"),
            tech_name=_str(data, "techName"),
            title=_str(data, "title"),
            question_order=_int(data, "questionOrder"),
            description=_str(data, "description"),
            tooltip_message=_str(data, "tooltipMessage"),
            read_only=_bool(data, "readOnly"),
            options=[Option.from_dict(_obj(o)) for o in _list(data, "options")],
            validation=_validation(data),
            repeating_section_grid=[
                Question.from_dict(_obj(q)) for q in _list(data, "repeatingSectionGrid")
            ],
            states=None
            if states is None
            else [State.from_dict(_obj(s)) for s in _list(data, "states")],
            default_value=_default_value(data),
            default_value_type=_opt_str(data, "defaultValueType"),
            dictionary_name=_opt_str(data, "dictionaryName"),
            multi_level_tree=_opt_bool(data, "multiLevelTree"),
            search_enabled=_opt_bool(data, "searchEnabled"),
            consent_section_config=None if consent is None else _obj(consent),
        )


@dataclass
class Question:
    """A field placed on the grid of a page or of a section."""

    x: int
    y: int
    rows: int
    cols: int
    field: Field
    min_item_rows: int | None = None

    def to_dict(self) -> JsonObject:
        return _drop_none(
            {
                "x": self.x,
                "y": self.y,
                "rows": self.rows,
                "cols": self.cols,
                "field": self.field.to_dict(),
                "minItemRows": self.min_item_rows,
            }
        )

    @classmethod
    def from_dict(cls, data: JsonObject) -> Question:
        min_item_rows = data.get("minItemRows")
        return cls(
            x=_int(data, "x"),
            y=_int(data, "y"),
            rows=_int(data, "rows"),
            cols=_int(data, "cols"),
            field=Field.from_dict(_obj(data.get("field"))),
            min_item_rows=None if min_item_rows is None else _int(data, "minItemRows"),
        )


@dataclass
class Tab:
    """A form page; type is MAIN or FINISH."""

    id: str
    title: str
    type: str
    questions: list[Question] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "questions": [q.to_dict() for q in self.questions],
        }

    @classmethod
    def from_dict(cls, data: JsonObject) -> Tab:
        return cls(
            id=_str(data, "id"),
            title=_str(data, "title"),
            type=_str(data, "type"),
            questions=[Question.from_dict(_obj(q)) for q in _list(data, "questions")],
        )


@dataclass
class FlowLink:
    """Transition between pages, by tab id."""

    id: str
    source: str
    target: str

    def to_dict(self) -> JsonObject:
        return {"id": self.id, "source": self.source, "target": self.target}

    @classmethod
    def from_dict(cls, data: JsonObject) -> FlowLink:
        return cls(_str(data, "id"), _str(data, "source"), _str(data, "target"))


@dataclass
class FormDefinition:
    title: str
    tabs: list[Tab] = field(default_factory=list)
    links: list[FlowLink] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return {
            "title": self.title,
            "tabs": [t.to_dict() for t in self.tabs],
            "flow": {"links": [link.to_dict() for link in self.links]},
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: JsonObject) -> FormDefinition:
        flow = _obj(data.get("flow"))
        return cls(
            title=_str(data, "title"),
            tabs=[Tab.from_dict(_obj(t)) for t in _list(data, "tabs")],
            links=[FlowLink.from_dict(_obj(link)) for link in _list(flow, "links")],
        )

    @classmethod
    def from_json(cls, text: str) -> FormDefinition:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise InvalidFormDefinition(f"not valid JSON: {error}") from error
        return cls.from_dict(_obj(data))


def _drop_none(data: JsonObject) -> JsonObject:
    return {key: value for key, value in data.items() if value is not None}


def _obj(value: JsonValue) -> JsonObject:
    if not isinstance(value, dict):
        raise InvalidFormDefinition(f"expected an object, got {type(value).__name__}")
    return value


def _list(data: JsonObject, key: str) -> list[JsonValue]:
    value = data.get(key)
    if not isinstance(value, list):
        raise InvalidFormDefinition(f"'{key}' must be a list")
    return value


def _str(data: JsonObject, key: str) -> str:
    return _as_str(data.get(key), key)


def _as_str(value: JsonValue, key: str) -> str:
    if not isinstance(value, str):
        raise InvalidFormDefinition(f"'{key}' must be a string")
    return value


def _opt_str(data: JsonObject, key: str) -> str | None:
    return None if data.get(key) is None else _str(data, key)


def _int(data: JsonObject, key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidFormDefinition(f"'{key}' must be an integer")
    return value


def _bool(data: JsonObject, key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise InvalidFormDefinition(f"'{key}' must be a boolean")
    return value


def _opt_bool(data: JsonObject, key: str) -> bool | None:
    return None if data.get(key) is None else _bool(data, key)


def _validation(data: JsonObject) -> list[str]:
    # Three reference fields have "validation": {} instead of []; read it as no validators (K-05).
    if data.get("validation") == {}:
        return []
    return [_as_str(v, "validation") for v in _list(data, "validation")]


def _default_value(data: JsonObject) -> str | list[str] | None:
    value = data.get("defaultValue")
    if isinstance(value, list):
        return [_as_str(v, "defaultValue") for v in value]
    return _opt_str(data, "defaultValue")


def _default_value_json(value: str | list[str] | None) -> JsonValue:
    return list(value) if isinstance(value, list) else value
