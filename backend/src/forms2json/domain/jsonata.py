"""JSONata conditions for field and section `states` (FR-08, FR-E3).

Builds only the shapes found in references 1 and 5 and in the technical rules: "field in a
section has answer X", its negation, and `and` / `or` of those.
"""

import json

from forms2json.domain.form_definition import State


def answer_is(value: str, tab: str, section: str, field: str) -> str:
    """True when `field` in `section` on page `tab` has answer `value` (RADIO, SELECT, CHECKBOX)."""
    return (
        f'("{_escape(value)}" in '
        f"tabs['{_escape(tab)}' in title]"
        f".questions['{_escape(section)}' in field.techName]"
        f".field.repeatingSectionGrid['{_escape(field)}' in field.techName]"
        ".field.__userAnswer)"
    )


def answer_is_not(value: str, tab: str, section: str, field: str) -> str:
    return "$not" + answer_is(value, tab, section, field)


# A value containing " and " / " or " only adds harmless extra parentheses.
def all_of(*conditions: str) -> str:
    return " and ".join(f"({c})" if " or " in c else c for c in conditions)


def any_of(*conditions: str) -> str:
    # `and` binds tighter than `or`, the parentheses only mirror the references' style.
    return " or ".join(f"({c})" if " and " in c else c for c in conditions)


def show(query: str) -> State:
    """SHOW state; valid for fields and sections."""
    return State("SHOW", query)


def read_only(query: str) -> State:
    """READ_ONLY state; the rules allow it on fields only, not on sections."""
    return State("READ_ONLY", query)


def _escape(text: str) -> str:
    # Values come from the LLM. JSON escapes are valid JSONata in both quote styles, but JSONata
    # has no \' escape, so an apostrophe inside a '...' string must go as '.
    return json.dumps(text, ensure_ascii=False)[1:-1].replace("'", "\\u0027")
