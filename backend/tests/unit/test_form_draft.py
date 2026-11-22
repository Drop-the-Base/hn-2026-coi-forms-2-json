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
            "page": "",
            "type": "RADIO",
            "required": True,
            "options": ["gotówka", "przelew"],
            "confidence": 0.85,
        },
        {
            "key": "numer_rachunku",
            "label": "Numer rachunku",
            "section": "Zwrot",
            "page": "",
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


def _object_schemas(schema: JsonObject) -> list[JsonObject]:
    defs = cast(JsonObject, schema["$defs"])
    objects = [schema, *(cast(JsonObject, d) for d in defs.values())]
    return [o for o in objects if o["type"] == "object"]


def test_schema_is_strict_json_schema() -> None:
    objects = _object_schemas(FORM_DRAFT_SCHEMA)

    json.dumps(FORM_DRAFT_SCHEMA)
    assert len(objects) == 8  # FormDraft + 7 nested models (title and addressee share Text)
    for obj in objects:
        assert obj["additionalProperties"] is False
        properties = cast(dict[str, JsonObject], obj["properties"])
        assert obj["required"] == list(properties)
        assert all("default" not in p for p in properties.values())


def test_draft_round_trips() -> None:
    assert FormDraft.from_dict(DRAFT).model_dump(mode="json") == DRAFT


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
        (["title"], "Wniosek", "dictionary"),
        (["title", "extra"], "x", "Extra inputs"),
        (["fields", 0, "confidence"], 1.5, "less than or equal to 1"),
        (["fields", 0, "confidence"], True, "valid number"),
        (["fields", 0, "type"], "WYSIWYG", "Input should be 'TEXT_FIELD'"),
        (["applicants", 0, "kind"], "ALIEN", "Input should be 'SELF'"),
        (["fields", 0, "options"], "gotówka", "valid list"),
        (["fees", 0, "amount"], "17", "valid number"),
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


def test_schema_requires_page_for_strict_output() -> None:
    field = cast(JsonObject, cast(JsonObject, FORM_DRAFT_SCHEMA["$defs"])["DraftField"])
    assert "page" in cast(list[str], field["required"])
    assert "default" not in cast(JsonObject, cast(JsonObject, field["properties"])["page"])
