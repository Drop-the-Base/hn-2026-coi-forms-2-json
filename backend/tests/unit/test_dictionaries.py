from importlib.resources import files

from forms2json.domain import dictionaries
from forms2json.domain.blocks.pages import applicant_page, contact_page
from forms2json.domain.form_definition import Field
from forms2json.domain.form_draft import ApplicantKind


def _fields() -> dict[str, Field]:
    tabs = [applicant_page("Urząd", list(ApplicantKind)), contact_page()]
    return {
        c.field.tech_name: c.field
        for tab in tabs
        for q in tab.questions
        for c in q.field.repeating_section_grid
    }


def test_templates_hold_no_dictionary_names_or_initial_data() -> None:
    # The names live only in domain.dictionaries, so renaming there renames them in every block.
    text = files("forms2json.domain.blocks").joinpath("templates.json").read_text("utf-8")

    assert "dictionaryName" not in text
    assert "EXTERNAL_SYSTEM" not in text


def test_every_mapped_field_exists_in_blocks() -> None:
    fields = _fields()

    assert set(dictionaries.DICTIONARY_FIELDS) <= set(fields)
    assert set(dictionaries.INITIAL_DATA) <= set(fields)


def test_dictionary_fields_use_configured_names() -> None:
    fields = _fields()

    assert fields["wojewodztwo"].dictionary_name == dictionaries.TERYT
    assert fields["wojewodztwo"].multi_level_tree is True
    assert fields["wojewodztwo"].default_value == []
    assert fields["kraj_siedziba"].dictionary_name == dictionaries.COUNTRIES
    assert fields["kraj_siedziba"].multi_level_tree is False
    assert fields["kraj_siedziba"].default_value == [dictionaries.DEFAULT_COUNTRY]


def test_initial_data_follows_k10_and_k11() -> None:
    fields = _fields()

    for name, source in dictionaries.INITIAL_DATA.items():
        assert fields[name].default_value == source
        assert fields[name].default_value_type == "EXTERNAL_SYSTEM"
    assert fields["imie"].default_value == "MLPZ.name"
    assert fields["nazwisko"].default_value == "MLPZ.surname"
    read_only = {name for name in dictionaries.INITIAL_DATA if fields[name].read_only}
    assert read_only == {"imie", "nazwisko", "numer_pesel"}


def test_sport_disciplines_dictionary_is_multi_level() -> None:
    field = Field("id", "CHECKBOX", "dyscypliny_sportowe", "Dyscypliny sportowe", 0)

    dictionaries.use_dictionary(field, dictionaries.SPORT_DISCIPLINES, [])

    assert field.dictionary_name == "DYSCYPLINY_SPORTOWE"
    assert field.multi_level_tree is True
