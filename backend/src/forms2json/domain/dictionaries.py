"""Dictionary names and initial data sources: change them only here (FR-E1, K-06, K-10, K-11).

Plain constants, not Settings: the names are part of the target platform's contract, not deployment.
"""

from forms2json.domain.form_definition import Field

TERYT = "TERYT_4G_DOWODOWY"  # 4 levels: voivodeship, county, commune, locality (K-06)
COUNTRIES = "Kraje"
SPORT_DISCIPLINES = "DYSCYPLINY_SPORTOWE"  # our proposal, docs/propozycja-slownika.md (FR-E2)
DEFAULT_COUNTRY = "Polska"
MULTI_LEVEL = {TERYT, SPORT_DISCIPLINES}

# Block fields (by techName) and the dictionary they use with its default answer.
DICTIONARY_FIELDS: dict[str, tuple[str, list[str]]] = {
    "kraj": (COUNTRIES, [DEFAULT_COUNTRY]),
    "kraj_siedziba": (COUNTRIES, [DEFAULT_COUNTRY]),
    "kraj_inna_osoba": (COUNTRIES, [DEFAULT_COUNTRY]),
    "wojewodztwo": (TERYT, []),
    "wojewodztwo_siedziba": (TERYT, []),
    "wojewodztwo_inna_osoba": (TERYT, []),
}

# Block fields (by techName) prefilled from registries: MLPZ per the Standardy (K-11).
INITIAL_DATA = {
    "imie": "MLPZ.name",
    "nazwisko": "MLPZ.surname",
    "numer_pesel": "PESEL.pesel",
    "kod_pocztowy": "MLPZ.postCode",
    "ulica": "MLPZ.street",
    "numer_budynku": "MLPZ.building",
    "numer_lokalu": "MLPZ.apartment",
    "numer_telefonu": "MLPZ.phoneNumber",
    "adres_e_mail": "MLPZ.email",
}
# K-10: identity is locked; address, phone and e-mail stay editable, as in the references.
READ_ONLY = {"imie", "nazwisko", "numer_pesel"}


def use_dictionary(field: Field, name: str, default: list[str]) -> None:
    field.dictionary_name = name
    field.multi_level_tree = name in MULTI_LEVEL
    field.default_value = list(default)


def use_initial_data(field: Field, source: str, read_only: bool) -> None:
    field.default_value = source
    field.default_value_type = "EXTERNAL_SYSTEM"
    field.read_only = read_only


def apply(field: Field) -> None:
    """Fill a block field's dictionary or initial data from the tables above."""
    if entry := DICTIONARY_FIELDS.get(field.tech_name):
        use_dictionary(field, *entry)
    if source := INITIAL_DATA.get(field.tech_name):
        use_initial_data(field, source, field.tech_name in READ_ONLY)
