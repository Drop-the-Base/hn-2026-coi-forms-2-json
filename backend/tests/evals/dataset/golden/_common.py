"""Shared steps of build_golden_2/3/4: FormDraft -> compose -> hand fixes -> <n>.json.

Run from backend/: `uv run python -m tests.evals.dataset.golden.build_golden_2` (-m, because the
scripts import this module). Ids are fresh uuids on every run, so a rebuild rewrites all ids.
"""

import html
from collections.abc import Iterator
from pathlib import Path

from forms2json.domain.compose import compose
from forms2json.domain.form_definition import Field, FormDefinition, JsonObject, JsonValue, Tab
from forms2json.domain.form_draft import FormDraft
from forms2json.domain.rules import Severity, check_rules
from forms2json.domain.standards import check_schema

GOLDEN = Path(__file__).parent


def sure(data: JsonValue) -> JsonValue:
    """Adds confidence 1.0 to every nested object: a golden draft is certain by definition."""
    if isinstance(data, list):
        return [sure(item) for item in data]
    if isinstance(data, dict):
        return {**{k: sure(v) for k, v in data.items()}, "confidence": 1.0}
    return data


def build(draft: JsonObject) -> FormDefinition:
    data = sure(draft)
    assert isinstance(data, dict)
    del data["confidence"]  # the draft root has none
    form, _ = compose(FormDraft.from_dict(data))
    return form


def fields(form: FormDefinition) -> Iterator[Field]:
    for tab in form.tabs:
        for q in tab.questions:
            yield q.field
            yield from (child.field for child in q.field.repeating_section_grid)


def field(form: FormDefinition, tech_name: str) -> Field:
    return next(f for f in fields(form) if f.tech_name == tech_name)


def tab(form: FormDefinition, title: str) -> Tab:
    return next(t for t in form.tabs if t.title == title)


def rename_tab(form: FormDefinition, old: str, new: str) -> None:
    """SHOW queries address pages by title, so they follow the rename."""
    tab(form, old).title = new
    for f in fields(form):
        for state in f.states or []:
            state.query = state.query.replace(f"tabs['{old}' in title]", f"tabs['{new}' in title]")


def html_text(*paragraphs: str) -> str:
    body = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    return f"<html><head></head><body>{body}</body></html>"


def save(form: FormDefinition, name: str) -> None:
    errors = [i for i in check_rules(form) if i.severity is Severity.ERROR]
    errors += check_schema(form.to_dict())
    assert not errors, errors
    (GOLDEN / f"{name}.json").write_text(form.to_json() + "\n", encoding="utf-8")
