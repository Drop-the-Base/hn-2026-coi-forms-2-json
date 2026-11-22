"""Accessibility and plain-language hints (FR-09, FR-T1) for the citizen-facing form.

They say where the form is hard to read, not that it is wrong, so they are INFO issues:
they reach the problem list but do not lower the confidence.
"""

import html
import re
from collections.abc import Iterator

from forms2json.domain.form_definition import FormDefinition
from forms2json.domain.rules import Issue, Severity, _is_section, _walk

# Thresholds tuned on the golden forms 1-9: they raise nothing there.
MAX_LABEL_CHARS = 100
MAX_LABEL_WORDS = 15
MAX_PARAGRAPH_WORDS = 80
MAX_FOG = 15.0  # Jasnopis: 13-15 is already "hard"; the official Standards blocks score 13-14
MIN_FOG_WORDS = 30  # FOG on a few words is noise
HARD_WORD_SYLLABLES = 4
TEXT_TYPES = {"TEXT_BLOCK", "INFO_SECTION"}
CHOICE_TYPES = {"RADIO", "SELECT", "CHECKBOX"}
INPUT_EXEMPT = TEXT_TYPES | {"CONSENT_SECTION"}
GENERIC_TITLE = re.compile(r"^\s*((strona|sekcja|część|krok|etap)\s*)?[\dIVX.\s]*$", re.IGNORECASE)
VOWEL_GROUP = re.compile(r"[aąeęioóuy]+", re.IGNORECASE)
WORD = re.compile(r"[^\W\d_]+")
SENTENCE_END = re.compile(r"[.!?;:]+(?:\s|$)")
BLOCK_TAG = re.compile(r"<\s*(?:/p|br|/li|/h\d|/div|/tr)\b[^>]*>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")


def check_accessibility(form: FormDefinition) -> list[Issue]:
    return [*_check_titles(form), *_check_fields(form)]


def fog_index(text: str) -> float:
    """Polish FOG (the Jasnopis FOG-PL idea): 0.4 * (words per sentence + % of 4+ syllable words).

    Syllables are vowel groups, so "nie" or "się" count as one.
    """
    words = WORD.findall(text)
    if not words:
        return 0.0
    sentences = max(1, len(SENTENCE_END.findall(text.strip() + " ")))
    hard = sum(len(VOWEL_GROUP.findall(w)) >= HARD_WORD_SYLLABLES for w in words)
    return 0.4 * (len(words) / sentences + 100 * hard / len(words))


def plain_text(markup: str) -> str:
    """Text of a TEXT_BLOCK's HTML, one paragraph per line."""
    return html.unescape(TAG.sub(" ", BLOCK_TAG.sub("\n", markup))).replace("\xa0", " ")


def _info(code: str, message: str, path: str) -> Issue:
    return Issue(code, message, path, Severity.INFO)


def _check_titles(form: FormDefinition) -> Iterator[Issue]:
    for t, tab in enumerate(form.tabs):
        if tab.type != "FINISH" and GENERIC_TITLE.match(tab.title):
            yield _info(
                "A-GENERIC-TITLE",
                f"Strona „{tab.title}” nie mówi, czego dotyczy: nadaj jej tytuł opisujący treść.",
                f"tabs[{t}]",
            )
    for p in _walk(form):
        if _is_section(p.field) and p.field.title.strip() and GENERIC_TITLE.match(p.field.title):
            yield _info(
                "A-GENERIC-TITLE",
                f"Sekcja „{p.field.title}” ({p.field.tech_name}) nie mówi, czego dotyczy: "
                "nadaj jej tytuł opisujący treść.",
                p.path,
            )


def _check_fields(form: FormDefinition) -> Iterator[Issue]:
    for p in _walk(form):
        field, name = p.field, p.field.tech_name
        if field.type in TEXT_TYPES:
            yield from _check_text(plain_text(field.description), name, p.path)
            continue
        if _is_section(field) or field.type in INPUT_EXEMPT:
            continue
        title = field.title.strip()
        if not title:
            yield _info(
                "A-LABEL",
                f"Pole {name} nie ma etykiety: czytnik ekranu nie powie, co wpisać.",
                p.path,
            )
        elif len(title) > MAX_LABEL_CHARS or len(title.split()) > MAX_LABEL_WORDS:
            yield _info(
                "A-LABEL",
                f"Etykieta pola {name} ma {len(title.split())} słów: skróć ją, "
                "a wyjaśnienie przenieś do opisu pola.",
                p.path,
            )
        # A SELECT may take its options from a dictionary instead.
        if field.type in CHOICE_TYPES and not field.dictionary_name and len(field.options) < 2:
            yield _info(
                "A-OPTIONS",
                f"Pole wyboru {name} ma {len(field.options)} opcji: nie ma z czego wybierać.",
                p.path,
            )


def _check_text(text: str, name: str, path: str) -> Iterator[Issue]:
    longest = max((len(WORD.findall(line)) for line in text.splitlines()), default=0)
    if longest > MAX_PARAGRAPH_WORDS:
        yield _info(
            "A-TEXT-WALL",
            f"Blok tekstu {name} ma akapit z {longest} słów: podziel go na krótsze akapity "
            "albo listę.",
            path,
        )
    if len(WORD.findall(text)) >= MIN_FOG_WORDS and (fog := fog_index(text)) > MAX_FOG:
        yield _info(
            "A-PLAIN-LANGUAGE",
            f"Tekst w {name} trudny w odbiorze (FOG ≈ {fog:.0f}): skróć zdania "
            "i zastąp długie słowa prostszymi.",
            path,
        )
