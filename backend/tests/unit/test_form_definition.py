import json
from pathlib import Path

import pytest

from forms2json.domain.form_definition import (
    FormDefinition,
    InvalidFormDefinition,
    JsonValue,
)

DATA = Path(__file__).parents[3] / "data"
REFERENCES = [
    *DATA.glob("1. */konfiguracja_form_*.json"),
    *DATA.glob("5. */konfiguracja_form_*.json"),
]


def _empty_validation_as_list(value: JsonValue) -> JsonValue:
    """The model reads the references' "validation": {} as [] (K-05); align the expected JSON."""
    if isinstance(value, list):
        return [_empty_validation_as_list(v) for v in value]
    if isinstance(value, dict):
        return {
            k: [] if k == "validation" and v == {} else _empty_validation_as_list(v)
            for k, v in value.items()
        }
    return value


def test_both_references_are_found() -> None:
    assert len(REFERENCES) == 2


@pytest.mark.parametrize("path", REFERENCES, ids=lambda p: p.parent.name[:2])
def test_reference_round_trips_through_model(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    result = json.loads(FormDefinition.from_json(text).to_json())

    assert result == _empty_validation_as_list(json.loads(text))


def test_section_children_are_serialized_under_repeating_section_grid() -> None:
    text = FormDefinition.from_json(REFERENCES[0].read_text(encoding="utf-8")).to_json()

    assert '"repeatingSectionGrid"' in text
    assert "repetingSectionGrid" not in text


def test_missing_required_key_is_rejected() -> None:
    with pytest.raises(InvalidFormDefinition, match="title"):
        FormDefinition.from_json('{"tabs": [], "flow": {"links": []}}')
