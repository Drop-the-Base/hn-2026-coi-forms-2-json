from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from forms2json.adapters.outbound.readers.docx_reader import DocxReader
from forms2json.adapters.outbound.readers.ods_reader import OdsReader
from forms2json.adapters.outbound.readers.xlsx_reader import XlsxReader
from forms2json.application.pipeline.compose_step import ComposeStep
from forms2json.application.pipeline.pii_guard_step import PiiGuardStep
from forms2json.application.pipeline.pipeline import Pipeline
from forms2json.application.pipeline.report_step import ReportStep
from forms2json.application.pipeline.understand_step import UnderstandStep
from forms2json.application.pipeline.validate_step import ValidateStep
from forms2json.application.ports.document_reader import DocumentReader
from forms2json.application.ports.llm_client import LlmClient, LlmResult, LlmUsage
from forms2json.domain.cost import CostRates
from forms2json.domain.document import Checkbox, NormalizedDocument, Page, Table, TextBlock
from forms2json.domain.pii import (
    is_account,
    is_id_card,
    is_nip,
    is_pesel,
    is_phone,
    is_regon,
    mask_pii,
)
from tests.unit.test_understand_step import VALID

PESEL = "44051401359"
IBAN = "PL61 1090 1014 0000 0712 1981 2874"


@pytest.mark.parametrize(
    ("validator", "valid", "invalid"),
    [
        (is_pesel, PESEL, "44051401358"),
        (is_pesel, "02270803624", "02270803628"),  # born in 2002 (month + 20)
        (is_nip, "5260250274", "5260250275"),
        (is_regon, "123456785", "123456786"),
        (is_regon, "12345678512347", "12345678512348"),
        (is_id_card, "ABA300000", "ABA300001"),
        (is_account, "PL61109010140000071219812874", "61109010140000071219812875"),
        (is_phone, "600123456", "000000000"),
    ],
)
def test_validator_accepts_valid_and_rejects_wrong_checksum(
    validator: Any, valid: str, invalid: str
) -> None:
    assert validator(valid)
    assert not validator(invalid)


@pytest.mark.parametrize(
    "placeholder",
    ["00000000000", "0000000000", "000000000", "44133101359", "00-000", "___", "........"],
)
def test_blank_form_placeholders_are_not_personal_data(placeholder: str) -> None:
    found: Counter[str] = Counter()

    assert mask_pii(f"PESEL/NIP: {placeholder}", found) == f"PESEL/NIP: {placeholder}"
    assert found == Counter()


def test_mask_replaces_each_kind_and_counts_it() -> None:
    found: Counter[str] = Counter()
    text = (
        f"PESEL {PESEL}, dowód ABA 300000, NIP 526-025-02-74, REGON 123456785, "
        f"konto {IBAN}, jan.kowalski@example.pl, tel. +48 600 123 456, 61 852 12 34"
    )

    assert mask_pii(text, found) == (
        "PESEL [PESEL], dowód [NR DOWODU], NIP [NIP], REGON [REGON], "
        "konto [IBAN], [E-MAIL], tel. [TELEFON], [TELEFON]"
    )
    assert found == Counter(
        {"PESEL": 1, "NR DOWODU": 1, "NIP": 1, "REGON": 1, "IBAN": 1, "E-MAIL": 1, "TELEFON": 2}
    )


FILLED = NormalizedDocument(
    (
        Page(
            1,
            (
                TextBlock(f"PESEL: {PESEL}", confidence=0.9),
                Table((("Nr rachunku", IBAN),)),
                Checkbox("kontakt: jan@example.pl", checked=True),
            ),
        ),
    )
)


def test_step_masks_a_filled_form() -> None:
    step = PiiGuardStep()

    masked = step.run(FILLED)

    assert masked.pages[0].blocks == (
        TextBlock("PESEL: [PESEL]", confidence=0.9),
        Table((("Nr rachunku", "[IBAN]"),)),
        Checkbox("kontakt: [E-MAIL]", checked=True),
    )
    assert step.found == Counter({"PESEL": 1, "IBAN": 1, "E-MAIL": 1})


def test_step_leaves_a_blank_form_with_office_contacts_unchanged() -> None:
    # The office's own e-mail and account sit in blank forms (training forms 1, 6, 7, 8).
    blank = NormalizedDocument(
        (Page(1, (TextBlock(f"PESEL: ...........  Opłata na rachunek {IBAN}, iod@urzad.pl"),)),)
    )
    step = PiiGuardStep()
    step.found = Counter({"PESEL": 1})  # a previous run's state must not leak

    assert step.run(blank) is blank
    assert step.found == Counter()


class RecordingLlm(LlmClient):
    def __init__(self) -> None:
        self.users: list[str] = []

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult:
        self.users.append(user)
        return LlmResult(VALID, LlmUsage(10, 5, 1.0))


def test_personal_data_never_reaches_the_llm_and_the_report_warns() -> None:
    llm = RecordingLlm()
    pii, understand, compose = PiiGuardStep(), UnderstandStep(llm, 100_000), ComposeStep()
    report = ReportStep(pii, understand, compose, 0.85, CostRates(0, 0, 0, "PLN"))
    pipeline = Pipeline([pii, understand, compose, ValidateStep(), report])

    result = pipeline.run(FILLED)

    assert isinstance(result, dict)
    assert PESEL not in llm.users[0] and "jan@example.pl" not in llm.users[0]
    assert PESEL not in result["source_text"]
    (warning,) = [i for i in result["issues"] if i["code"] == "PII-MASKED"]
    assert warning["severity"] == "WARNING"
    assert warning["message"] == (
        "Plik wygląda na wypełniony: PESEL (1), IBAN (1), E-MAIL (1); "
        "dane zamaskowano przed wysłaniem do modelu."
    )
    assert result["pii"] == {"PESEL": 1, "IBAN": 1, "E-MAIL": 1}


DATA = Path(__file__).parents[3] / "data"
READERS: dict[str, DocumentReader] = {
    ".docx": DocxReader(),
    ".xlsx": XlsxReader(),
    ".ods": OdsReader(),
}
# Training forms only: the hold-out set lives elsewhere and stays unread (NFR-11).
BLANKS = [f for f in sorted(DATA.glob("[1-9]. */*")) if f.suffix.lower() in READERS]


@pytest.mark.parametrize("path", BLANKS, ids=lambda p: p.name)
def test_training_blank_forms_raise_no_alarm(path: Path) -> None:
    step = PiiGuardStep()

    step.run(READERS[path.suffix.lower()].read(path.read_bytes()))

    assert step.found == Counter()
