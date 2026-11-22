"""Field `validation` entries (K-05, FR-E6): the one place that maps a label to validators.

The generator sets them with `validation_for`; the S-VALIDATOR standard warns when they are missing.
"""

import re

from forms2json.domain.rules import VALIDATORS

# (pattern on title or techName, validator the Standards require). The rules allow no phone
# validator, so a phone field gets only REQUIRED.
EXPECTED_VALIDATORS = [
    (re.compile(r"e-?mail|e_mail", re.IGNORECASE), "EMAIL"),
    (re.compile(r"pesel", re.IGNORECASE), "PESEL"),
    (re.compile(r"\bnip\b|(^|_)nip(_|$)", re.IGNORECASE), "NIP"),
    (re.compile(r"regon", re.IGNORECASE), "REGON"),
    (re.compile(r"kod pocztowy|kod_pocztowy", re.IGNORECASE), "ZIP_CODE"),
    # "dowodu osobistego" only: "dowód wpłaty" or the dog's "rodowód" are no ID card.
    (re.compile(r"\bdow[oó]d\w*[ _]osobist", re.IGNORECASE), "SERIAL_NUMBER_ID_CARD"),
]
assert {v for _, v in EXPECTED_VALIDATORS} <= VALIDATORS
# Standards: a postal code outside Poland has no validation.
FOREIGN = re.compile(r"zagranica")


def expected_validators(title: str, tech_name: str) -> list[str]:
    """Validators the Standards require for a field with this label, without REQUIRED."""
    if FOREIGN.search(tech_name):
        return []
    return [v for p, v in EXPECTED_VALIDATORS if p.search(title) or p.search(tech_name)]


def validation_for(title: str, tech_name: str, required: bool) -> list[str]:
    """K-05: optional field gives [] (never {}); required gives ["REQUIRED", *validators]."""
    return ["REQUIRED", *expected_validators(title, tech_name)] if required else []
