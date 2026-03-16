from __future__ import annotations

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import cv2
import pypdf
import pypdfium2 as pdfium

from pdf_ocr_ui.settings import OCRSettings
from pdf_ocr_ui.services.ocr_service import ocr_image_with_layout
from pdf_ocr_ui.services.article_service import split_into_articles
from pdf_ocr_ui.services.orthography_service import detect_pre_reform
from pdf_ocr_ui.services.pre_reform_translation_service import translate_text
from pdf_ocr_ui.types import ArticleText, DocumentText, PageText


def _needs_ocr(text: str, min_native_chars: int) -> bool:
    return len(text.strip()) < min_native_chars


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _extract_native_text(reader: pypdf.PdfReader) -> tuple[list[str], list[str]]:
    native_clean: list[str] = []
    native_raw: list[str] = []
    for page in reader.pages:
        raw_text = page.extract_text() or ""
        native_raw.append(raw_text)
        native_clean.append(_normalize_text(raw_text))
    return native_clean, native_raw


def _render_pages(pdf_bytes: bytes, page_indices: list[int], settings: OCRSettings):
    doc = pdfium.PdfDocument(pdf_bytes)
    scale = settings.render_dpi / 72
    rendered = {}

    for idx in page_indices:
        page = doc[idx]
        bitmap = page.render(scale=scale)
        rendered[idx] = cv2.cvtColor(bitmap.to_numpy(), cv2.COLOR_RGB2BGR)

    return rendered


def extract_text_from_pdf(
    pdf_bytes: bytes, settings: OCRSettings
) -> tuple[DocumentText, list[PageText], list[ArticleText]]:
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    native_text_by_page, native_raw_by_page = _extract_native_text(reader)

    pages_total = len(native_text_by_page)
    if pages_total == 0:
        return DocumentText(pages_total=0, pages_ocr=0, text="", orthography=detect_pre_reform("")), [], []

    ocr_indices = [
        i for i, txt in enumerate(native_text_by_page) if _needs_ocr(txt, settings.min_native_chars)
    ]

    ocr_text_by_page: dict[int, str] = {}
    ocr_raw_by_page: dict[int, str] = {}
    if ocr_indices:
        rendered_pages = _render_pages(pdf_bytes, ocr_indices, settings)
        workers = max(1, min(settings.max_workers, len(ocr_indices)))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                idx: pool.submit(ocr_image_with_layout, rendered_pages[idx], settings)
                for idx in ocr_indices
            }
            for idx, future in futures.items():
                clean_text, raw_text = future.result()
                ocr_text_by_page[idx] = _normalize_text(clean_text)
                ocr_raw_by_page[idx] = raw_text

    page_results: list[PageText] = []
    raw_pages_for_articles: list[tuple[int, str]] = []
    merged: list[str] = []
    analysis_texts: list[str] = []

    for page_idx, native_text in enumerate(native_text_by_page):
        ocr_text = ocr_text_by_page.get(page_idx, "")
        ocr_raw = ocr_raw_by_page.get(page_idx, "")
        native_raw = native_raw_by_page[page_idx] if page_idx < len(native_raw_by_page) else ""
        use_ocr = len(ocr_text) > len(native_text) * 0.7 and len(ocr_text) >= settings.min_native_chars // 2

        if use_ocr:
            final_text = ocr_text
            method = "ocr"
            raw_pages_for_articles.append((page_idx + 1, ocr_raw))
        else:
            final_text = native_text
            method = "native"
            raw_pages_for_articles.append((page_idx + 1, native_raw))

        page_results.append(PageText(page_number=page_idx + 1, method=method, text=final_text))
        merged.append(f"===== Page {page_idx + 1} ({method}) =====\n{final_text}")
        analysis_texts.append(final_text)

    orthography = detect_pre_reform("\n".join(analysis_texts))
    modern_text = None
    if orthography.pre_reform:
        modern_pages: list[str] = []
        for page in page_results:
            translated = translate_text(page.text)
            modern_pages.append(f"===== Page {page.page_number} ({page.method}) =====\n{translated}")
        modern_text = "\n\n".join(modern_pages).strip()
    document = DocumentText(
        pages_total=pages_total,
        pages_ocr=sum(1 for p in page_results if p.method == "ocr"),
        text="\n\n".join(merged).strip(),
        orthography=orthography,
        modern_text=modern_text,
    )
    articles = split_into_articles(raw_pages_for_articles)
    return document, page_results, articles
