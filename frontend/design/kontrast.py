"""Liczy kontrast WCAG 2.1 dla par kolorów z tokens.css i drukuje tabelę Markdown do DESIGN.md.

Uruchom: python3 frontend/design/kontrast.py  (kod wyjścia 1, gdy któraś para nie spełnia progu)
"""

import re
import sys
from pathlib import Path

TEXT, UI = 4.5, 3.0

# (tekst/element, tło, próg, opis)
PAIRS = [
    ("ink", "paper", TEXT, "tekst / papier"),
    ("ink", "sheet", TEXT, "tekst / arkusz"),
    ("ink", "paper-2", TEXT, "tekst / hover wiersza"),
    ("muted", "paper", TEXT, "tekst pomocniczy / papier"),
    ("muted", "sheet", TEXT, "tekst pomocniczy / arkusz"),
    ("muted", "paper-2", TEXT, "tekst pomocniczy / hover wiersza"),
    ("on-shell", "shell", TEXT, "tekst paska aplikacji"),
    ("on-shell-muted", "shell", TEXT, "tekst pomocniczy paska aplikacji"),
    ("accent", "sheet", TEXT, "link, przycisk drugorzędny / arkusz"),
    ("accent", "paper", TEXT, "link / papier"),
    ("accent", "accent-subtle", TEXT, "akcent / zaznaczenie, hover"),
    ("on-accent", "accent", TEXT, "tekst przycisku głównego"),
    ("on-accent", "accent-hover", TEXT, "tekst przycisku głównego, hover"),
    ("error", "sheet", TEXT, "błąd / arkusz"),
    ("error", "error-bg", TEXT, "błąd, pewność niska / tło"),
    ("warning", "warning-bg", TEXT, "ostrzeżenie, pewność średnia / tło"),
    ("warning", "sheet", TEXT, "ostrzeżenie / arkusz"),
    ("success", "success-bg", TEXT, "sukces, pewność wysoka / tło"),
    ("success", "sheet", TEXT, "sukces / arkusz"),
    ("code-key", "code-bg", TEXT, "edytor: klucz"),
    ("code-string", "code-bg", TEXT, "edytor: tekst"),
    ("code-number", "code-bg", TEXT, "edytor: liczba"),
    ("code-punct", "code-bg", TEXT, "edytor: interpunkcja"),
    ("code-key", "code-current", TEXT, "edytor: klucz w bieżącym elemencie"),
    ("code-string", "code-current", TEXT, "edytor: tekst w bieżącym elemencie"),
    ("code-line-no", "code-gutter", TEXT, "edytor: numer linii"),
    ("eu-ink", "eu-card", TEXT, "podgląd: tekst / karta"),
    ("eu-label", "eu-card", TEXT, "podgląd: etykieta / karta"),
    ("eu-ink", "eu-readonly", TEXT, "podgląd: pole tylko do odczytu"),
    ("eu-ink", "eu-ground", TEXT, "podgląd: tytuł / tło"),
    ("sheet", "eu-primary", TEXT, "podgląd: przycisk „Dalej”"),
    ("field-border", "sheet", UI, "ramka pola / arkusz"),
    ("field-border", "paper", UI, "ramka pola / papier"),
    ("focus", "sheet", UI, "fokus / arkusz"),
    ("focus", "paper", UI, "fokus / papier"),
    ("focus", "accent-subtle", UI, "fokus / zaznaczony wiersz"),
    ("focus-on-shell", "shell", UI, "fokus / pasek aplikacji"),
    ("error", "sheet", UI, "ramka pola z błędem, znacznik niski / arkusz"),
    ("conf-medium-mark", "sheet", UI, "kreskowanie znacznika średniego / arkusz"),
    ("conf-high-mark", "sheet", UI, "obrys znacznika wysokiego / arkusz"),
    ("eu-border", "eu-card", UI, "podgląd: ramka pola"),
    ("accent", "eu-card", UI, "zaznaczenie elementu w podglądzie"),
]


def load_tokens(css: str) -> dict[str, str]:
    raw = dict(re.findall(r"--color-([\w-]+):\s*([^;]+);", css))
    resolved = {}
    for name, value in raw.items():
        while (ref := re.fullmatch(r"var\(--color-([\w-]+)\)", value.strip())):
            value = raw[ref.group(1)]
        resolved[name] = value.strip()
    return resolved


def luminance(hex_color: str) -> float:
    channels = [int(hex_color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(fg: str, bg: str) -> float:
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    assert round(ratio("#000000", "#FFFFFF"), 2) == 21.0  # samosprawdzenie wzoru
    tokens = load_tokens((Path(__file__).parent / "tokens.css").read_text(encoding="utf-8"))
    print("| Para | Kolor | Tło | Wynik | Próg | |")
    print("|---|---|---|---|---|---|")
    failed = 0
    for fg, bg, threshold, label in PAIRS:
        value = ratio(tokens[fg], tokens[bg])
        ok = value >= threshold
        failed += not ok
        verdict = "spełnia" if ok else "**NIE SPEŁNIA**"
        print(f"| {label} | `{fg}` {tokens[fg]} | `{bg}` {tokens[bg]} | {value:.2f}:1 | {threshold}:1 | {verdict} |")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
