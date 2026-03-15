from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OrthographyReport:
    pre_reform: bool
    score: float
    archaic_letters_count: int
    archaic_letters_found: str
    archaic_letters_ratio: float
    terminal_hard_sign_count: int
    terminal_hard_sign_ratio: float
    total_words: int


@dataclass(slots=True)
class PageText:
    page_number: int
    method: str
    text: str


@dataclass(slots=True)
class ArticleText:
    article_id: int
    title: str
    page_start: int
    page_end: int
    text: str


@dataclass(slots=True)
class DocumentText:
    pages_total: int
    pages_ocr: int
    text: str
    orthography: OrthographyReport | None = None
