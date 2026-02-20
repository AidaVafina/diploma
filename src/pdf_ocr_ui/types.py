from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PageText:
    page_number: int
    method: str
    text: str


@dataclass(slots=True)
class DocumentText:
    pages_total: int
    pages_ocr: int
    text: str
