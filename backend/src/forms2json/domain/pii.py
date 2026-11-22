"""Personal data in an uploaded file: a filled-in application instead of a blank form (NFR-06).

Identifiers count only with a valid checksum (and PESEL with a real birth date), so blank-form
placeholders like "00-000", "___", "........" or a sample "00000000000" stay as they are.
Blank forms carry the office's own e-mail, phone and bank account (training forms 1, 6, 7, 8), so
only a personal ID (PESEL, ID card) marks a file as filled; then every kind gets masked.
"""

import re
from collections import Counter
from collections.abc import Callable
from datetime import date

# PESEL month offset → century: 1900s +0, 2000s +20, 2100s +40, 2200s +60, 1800s +80.
_CENTURY = {0: 1900, 1: 2000, 2: 2100, 3: 2200, 4: 1800}


def _weighted_sum(digits: str, weights: tuple[int, ...]) -> int:
    return sum(int(d) * w for d, w in zip(digits, weights, strict=False))


def _placeholder(digits: str) -> bool:
    # "0000000000" passes the NIP and REGON checksums, but it is a sample, not anyone's number.
    return len(set(digits)) == 1


def is_pesel(digits: str) -> bool:
    if len(digits) != 11 or not digits.isdigit():
        return False
    check = (10 - _weighted_sum(digits, (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)) % 10) % 10
    month = int(digits[2:4])
    try:
        date(int(digits[:2]) + _CENTURY[month // 20], month % 20, int(digits[4:6]))
    except KeyError, ValueError:
        return False
    return check == int(digits[10])


def is_nip(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit() or _placeholder(digits):
        return False
    return _weighted_sum(digits, (6, 5, 7, 2, 3, 4, 5, 6, 7)) % 11 == int(digits[9])


def is_regon(digits: str) -> bool:
    weights = {9: (8, 9, 2, 3, 4, 5, 6, 7), 14: (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)}
    if len(digits) not in weights or not digits.isdigit() or _placeholder(digits):
        return False
    return _weighted_sum(digits, weights[len(digits)]) % 11 % 10 == int(digits[-1])


def is_id_card(serial: str) -> bool:
    """Polish ID card: 3 letters and 6 digits, the first digit is the check digit."""
    if not re.fullmatch(r"[A-Z]{3}\d{6}", serial):
        return False
    values = [int(c, 36) for c in serial]  # A=10 … Z=35
    rest = values[:3] + values[4:]
    return sum(v * w for v, w in zip(rest, (7, 3, 1, 7, 3, 1, 7, 3), strict=True)) % 10 == values[3]


def is_account(number: str) -> bool:
    """Polish IBAN or bank account number (26 digits, optional "PL"), checked mod 97."""
    digits = number.removeprefix("PL")
    if len(digits) != 26 or not digits.isdigit():
        return False
    return int(digits[2:] + "2521" + digits[:2]) % 97 == 1  # "PL" = 25 21


def is_phone(digits: str) -> bool:
    # No checksum: a Polish number has 9 digits and never starts with 0.
    return digits.removeprefix("48")[:1] != "0" and not _placeholder(digits)


def _any(_: str) -> bool:
    return True


# Digit runs: no digit (or "+" of a phone prefix) right before, no digit right after.
_NUMBER = r"(?<![\d+]){}(?!\d)"
_PHONE = r"(?:\+?48[ -]?)?(?:\d{3}[ -]?\d{3}[ -]?\d{3}|\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2})"

type Validator = Callable[[str], bool]

# Longest numbers first: a masked number cannot be found again as a shorter one.
_DETECTORS: list[tuple[str, re.Pattern[str], Validator]] = [
    ("IBAN", re.compile(r"(?<!\w)(?:PL ?)?\d{2}(?: ?\d{4}){6}(?!\d)"), is_account),
    ("REGON", re.compile(_NUMBER.format(r"\d{14}")), is_regon),
    ("PESEL", re.compile(_NUMBER.format(r"\d{11}")), is_pesel),
    (
        "NIP",
        re.compile(_NUMBER.format(r"(?:\d{3}-?\d{3}-?\d{2}-?\d{2}|\d{3}-\d{2}-\d{2}-\d{3})")),
        is_nip,
    ),
    ("REGON", re.compile(_NUMBER.format(r"\d{9}")), is_regon),
    ("NR DOWODU", re.compile(r"(?<![A-Za-z])[A-Z]{3} ?\d{6}(?!\d)"), is_id_card),
    # RFC 5321 lengths (64 local, 63 per label) bound the backtracking: unbounded runs made a
    # long word without "@" quadratic, a crafted file could hold the worker for hours.
    ("E-MAIL", re.compile(r"[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63})+"), _any),
    ("TELEFON", re.compile(_NUMBER.format(_PHONE)), is_phone),
]

PERSONAL_IDS = frozenset({"PESEL", "NR DOWODU"})


def mask_pii(text: str, found: Counter[str]) -> str:
    """Replaces personal data with its kind, e.g. "[PESEL]", and counts each kind in `found`."""
    for kind, pattern, valid in _DETECTORS:

        def replace(match: re.Match[str], kind: str = kind, valid: Validator = valid) -> str:
            if not valid(re.sub(r"[\s+-]", "", match[0])):
                return match[0]
            found[kind] += 1
            return f"[{kind}]"

        text = pattern.sub(replace, text)
    return text


def pii_summary(found: Counter[str]) -> str:
    counts = ", ".join(f"{kind} ({n})" for kind, n in found.most_common())
    return f"Plik wygląda na wypełniony: {counts}; dane zamaskowano przed wysłaniem do modelu."
