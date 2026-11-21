import pytest

from forms2json.domain.validators import validation_for


@pytest.mark.parametrize(
    ("title", "tech_name", "required", "expected"),
    [
        ("Imię", "imie", True, ["REQUIRED"]),
        ("Nazwisko", "nazwisko", True, ["REQUIRED"]),
        ("PESEL", "pesel", True, ["REQUIRED", "PESEL"]),
        ("Adres e-mail", "adres_email", True, ["REQUIRED", "EMAIL"]),
        ("Adres e-mail", "adres_email", False, []),
        ("Kod pocztowy", "kod_pocztowy", True, ["REQUIRED", "ZIP_CODE"]),
        ("Kod pocztowy", "kod_pocztowy_zagranica", True, ["REQUIRED"]),
        ("NIP", "nip", True, ["REQUIRED", "NIP"]),
        ("REGON", "regon", True, ["REQUIRED", "REGON"]),
        ("Numer telefonu", "numer_telefonu", True, ["REQUIRED"]),
        ("Uwagi", "uwagi", False, []),
    ],
)
def test_validation_for(title: str, tech_name: str, required: bool, expected: list[str]) -> None:
    assert validation_for(title, tech_name, required) == expected
