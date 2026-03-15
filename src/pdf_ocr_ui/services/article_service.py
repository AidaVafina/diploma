from __future__ import annotations

import re

from pdf_ocr_ui.types import ArticleText

_HEADING_PATTERNS = [
    re.compile(r"^(статья|глава|раздел|параграф|часть)\b", re.IGNORECASE),
    re.compile(r"^(№|no\.?|n\.)\s*\d+", re.IGNORECASE),
    re.compile(r"^\d+[.)]\s+\S+"),
    re.compile(r"^[IVXLCDM]+[.)]\s+\S+", re.IGNORECASE),
    re.compile(r"^\d{1,2}[./]\d{1,2}[./]\d{2,4}\b"),
]


def _normalize_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cleaned = " ".join(raw.split())
        lines.append(cleaned)
    return lines


def _is_heading_line(line: str) -> bool:
    s = line.strip()
    if len(s) < 4 or len(s) > 120:
        return False
    if re.search(r"[.?!;:]$", s):
        return False
    if any(pat.match(s) for pat in _HEADING_PATTERNS):
        return True

    letters = [ch for ch in s if ch.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(ch.isupper() for ch in letters) / len(letters)
    if upper_ratio >= 0.7:
        return True

    words = s.split()
    if 1 <= len(words) <= 8:
        title_like = sum(1 for w in words if w and w[0].isupper()) / len(words)
        if title_like >= 0.8:
            return True
    return False


def _infer_title(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s[:120]
    return "Без заголовка"


def split_into_articles(page_texts: list[tuple[int, str]]) -> list[ArticleText]:
    articles: list[ArticleText] = []
    current_lines: list[str] = []
    current_title = ""
    page_start: int | None = None
    page_end: int | None = None
    article_id = 1
    prev_blank = True

    def flush() -> None:
        nonlocal article_id, current_lines, current_title, page_start, page_end, prev_blank
        if not current_lines:
            return
        text = "\n".join(current_lines).strip()
        if not text:
            current_lines = []
            current_title = ""
            page_start = None
            page_end = None
            prev_blank = True
            return
        title = current_title or _infer_title(text)
        articles.append(
            ArticleText(
                article_id=article_id,
                title=title,
                page_start=page_start or 1,
                page_end=page_end or page_start or 1,
                text=text,
            )
        )
        article_id += 1
        current_lines = []
        current_title = ""
        page_start = None
        page_end = None
        prev_blank = True

    for page_number, raw_text in page_texts:
        lines = _normalize_lines(raw_text)
        non_empty_seen = 0
        for line in lines:
            if line == "":
                prev_blank = True
                if current_lines and current_lines[-1] != "":
                    current_lines.append("")
                continue

            non_empty_seen += 1
            at_page_start = non_empty_seen <= 3

            if _is_heading_line(line) and (prev_blank or at_page_start):
                if current_lines:
                    flush()
                current_title = line
                current_lines = [line]
                page_start = page_number
                page_end = page_number
                prev_blank = False
                continue

            prev_blank = False
            if not current_lines:
                page_start = page_number
            page_end = page_number
            current_lines.append(line)

    flush()
    return articles
