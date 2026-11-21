import copy
import json
from typing import cast

import pytest

from forms2json.domain.form_definition import JsonObject, JsonValue
from forms2json.domain.form_draft import FORM_DRAFT_SCHEMA, FormDraft, InvalidFormDraft

DRAFT: JsonObject = {
    "title": {"value": "Wniosek o zwrot opłaty skarbowej", "confidence": 0.95},
    "addressee": {"value": "Urząd Miasta Testowo", "confidence": 0.9},
    "applicants": [
        {"kind": "SELF", "confidence": 1.0},
        {"kind": "PROXY", "confidence": 0.6},
    ],
    "fields": [
        {
            "key": "sposob_zwrotu",
            "label": "Sposób zwrotu",
            "section": "Zwrot",
            "type": "RADIO",
            "required": True,
            "options": ["gotówka", "przelew"],
            "confidence": 0.85,
        },
        {
            "key": "numer_rachunku",
            "label": "Numer rachunku",
            "section": "Zwrot",
            "type": "TEXT_FIELD",
            "required": True,
            "options": [],
            "confidence": 0.8,
        },
    ],
    "conditions": [
        {
            "target": "numer_rachunku",
            "source": "sposob_zwrotu",
            "value": "przelew",
            "confidence": 0.75,
        }
    ],
    "attachments": [{"name": "Pełnomocnictwo", "required": False, "confidence": 0.7}],
    "fees": [{"description": "Opłata skarbowa", "amount": 17, "confidence": 0.9}],
    "consents": [{"text": "Oświadczam, że dane są prawdziwe.", "required": True, "confidence": 1}],
}


def _validate(schema: JsonValue, value: JsonValue) -> None:
    """Checks the JSON Schema subset FORM_DRAFT_SCHEMA uses; there is no jsonschema dependency."""
    assert isinstance(schema, dict)
    types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    python_types = {
        "object": dict,
        "array": list,
        "string": str,
        "boolean": bool,
        "number": int | float,
        "null": type(None),
    }
    assert any(isinstance(value, python_types[str(t)]) for t in types), (schema, value)
    if "enum" in schema:
        assert isinstance(schema["enum"], list) and value in schema["enum"]
    if isinstance(value, int | float) and "minimum" in schema:
        assert schema["minimum"] <= value <= schema["maximum"]  # type: ignore[operator]
    if isinstance(value, list):
        for item in value:
            _validate(schema["items"], item)
    if isinstance(value, dict):
        properties = schema["properties"]
        assert isinstance(properties, dict)
        assert set(value) == set(properties)
        for key, item in value.items():
            _validate(properties[key], item)


def _object_schemas(schema: JsonObject) -> list[JsonObject]:
    if schema["type"] == "array":
        return _object_schemas(cast(JsonObject, schema["items"]))
    if schema["type"] != "object":
        return []
    properties = cast(JsonObject, schema["properties"])
    return [schema] + [o for p in properties.values() for o in _object_schemas(cast(JsonObject, p))]


def test_schema_is_strict_json_schema() -> None:
    objects = _object_schemas(FORM_DRAFT_SCHEMA)

    json.dumps(FORM_DRAFT_SCHEMA)
    assert FORM_DRAFT_SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert len(objects) == 9
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])  # type: ignore[arg-type]


def test_schema_accepts_sample_draft() -> None:
    _validate(FORM_DRAFT_SCHEMA, DRAFT)


def test_draft_round_trips_and_matches_schema() -> None:
    result = FormDraft.from_dict(DRAFT).to_dict()

    assert result == DRAFT
    _validate(FORM_DRAFT_SCHEMA, json.loads(json.dumps(result)))


def _broken(path: list[str | int], value: JsonValue) -> JsonObject:
    data = copy.deepcopy(DRAFT)
    target: JsonValue = data
    for step in path[:-1]:
        target = target[step]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    return data


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (["title"], "Wniosek", "object"),
        (["fields", 0, "confidence"], 1.5, "between 0 and 1"),
        (["fields", 0, "confidence"], True, "number"),
        (["fields", 0, "type"], "WYSIWYG", "unknown value"),
        (["applicants", 0, "kind"], "ALIEN", "unknown value"),
        (["fields", 0, "options"], "gotówka", "list"),
        (["fees", 0, "amount"], "17 zł", "number"),
        (["fields", 1, "key"], "sposob_zwrotu", "unique"),
        (["conditions", 0, "source"], "brak_pola", "unknown field"),
    ],
)
def test_invalid_draft_is_rejected(path: list[str | int], value: JsonValue, message: str) -> None:
    with pytest.raises(InvalidFormDraft, match=message):
        FormDraft.from_dict(_broken(path, value))


def test_fee_without_amount_is_accepted() -> None:
    draft = FormDraft.from_dict(_broken(["fees", 0, "amount"], None))

    assert draft.fees[0].amount is None
