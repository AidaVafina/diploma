from __future__ import annotations

import re

from pdf_ocr_ui.types import OrthographyReport

_ARCHAIC_LETTERS = "ѣѢіІѳѲѵѴ"
_CYRILLIC_WORD_RE = re.compile(r"[А-Яа-яЁёѢѣІіѲѳѴѵЪъЬь]+")
_CONSONANTS = set("бвгджзйклмнпрстфхцчшщ")


def _count_archaic_letters(text: str) -> tuple[int, str]:
    count = 0
    found = set()
    for ch in text:
        if ch in _ARCHAIC_LETTERS:
            count += 1
            found.add(ch)
    return count, "".join(sorted(found))


def _count_terminal_hard_sign(words: list[str]) -> int:
    count = 0
    for word in words:
        if len(word) < 2:
            continue
        if not (word.endswith("ъ") or word.endswith("Ъ")):
            continue
        prev = word[-2].lower()
        if prev in _CONSONANTS:
            count += 1
    return count


def detect_pre_reform(text: str) -> OrthographyReport:
    if not text:
        return OrthographyReport(
            pre_reform=False,
            score=0.0,
            archaic_letters_count=0,
            archaic_letters_found="",
            archaic_letters_ratio=0.0,
            terminal_hard_sign_count=0,
            terminal_hard_sign_ratio=0.0,
            total_words=0,
        )

    words = _CYRILLIC_WORD_RE.findall(text)
    total_words = len(words)
    archaic_letters_count, archaic_letters_found = _count_archaic_letters(text)
    terminal_hard_sign_count = _count_terminal_hard_sign(words)

    total_letters = sum(1 for ch in text if ch.isalpha())
    archaic_letters_ratio = archaic_letters_count / max(total_letters, 1)
    terminal_hard_sign_ratio = terminal_hard_sign_count / max(total_words, 1)

    has_archaic = archaic_letters_count > 0
    has_terminal_hard_sign = terminal_hard_sign_count >= 3 and terminal_hard_sign_ratio >= 0.02
    pre_reform = has_archaic or has_terminal_hard_sign

    score = 0.0
    if has_archaic:
        score += 0.7
        score += min(0.2, archaic_letters_count * 0.02)
    if terminal_hard_sign_ratio > 0:
        score += min(0.3, terminal_hard_sign_ratio / 0.05 * 0.3)
    score = min(1.0, score)

    return OrthographyReport(
        pre_reform=pre_reform,
        score=score,
        archaic_letters_count=archaic_letters_count,
        archaic_letters_found=archaic_letters_found,
        archaic_letters_ratio=archaic_letters_ratio,
        terminal_hard_sign_count=terminal_hard_sign_count,
        terminal_hard_sign_ratio=terminal_hard_sign_ratio,
        total_words=total_words,
    )
