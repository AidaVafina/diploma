from __future__ import annotations

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import cv2
import pypdf
import pypdfium2 as pdfium

from pdf_ocr_ui.settings import OCRSettings
from pdf_ocr_ui.services.ocr_service import ocr_image
from pdf_ocr_ui.types import DocumentText, PageText


def _needs_ocr(text: str, min_native_chars: int) -> bool:
    return len(text.strip()) < min_native_chars


def _extract_native_text(reader: pypdf.PdfReader) -> list[str]:
    native: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        native.append(" ".join(text.split()))
    return native


def _render_pages(pdf_bytes: bytes, page_indices: list[int], settings: OCRSettings):
    doc = pdfium.PdfDocument(pdf_bytes)
    scale = settings.render_dpi / 72
    rendered = {}

    for idx in page_indices:
        page = doc[idx]
        bitmap = page.render(scale=scale)
        rendered[idx] = cv2.cvtColor(bitmap.to_numpy(), cv2.COLOR_RGB2BGR)

    return rendered


def extract_text_from_pdf(pdf_bytes: bytes, settings: OCRSettings) -> tuple[DocumentText, list[PageText]]:
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    native_text_by_page = _extract_native_text(reader)

    pages_total = len(native_text_by_page)
    if pages_total == 0:
        return DocumentText(pages_total=0, pages_ocr=0, text=""), []

    ocr_indices = [
        i for i, txt in enumerate(native_text_by_page) if _needs_ocr(txt, settings.min_native_chars)
    ]

    ocr_text_by_page: dict[int, str] = {}
    if ocr_indices:
        rendered_pages = _render_pages(pdf_bytes, ocr_indices, settings)
        workers = max(1, min(settings.max_workers, len(ocr_indices)))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                idx: pool.submit(ocr_image, rendered_pages[idx], settings)
                for idx in ocr_indices
            }
            for idx, future in futures.items():
                ocr_text_by_page[idx] = " ".join((future.result() or "").split())

    page_results: list[PageText] = []
    merged: list[str] = []

    for page_idx, native_text in enumerate(native_text_by_page):
        ocr_text = ocr_text_by_page.get(page_idx, "")
        use_ocr = len(ocr_text) > len(native_text) * 0.7 and len(ocr_text) >= settings.min_native_chars // 2

        if use_ocr:
            final_text = ocr_text
            method = "ocr"
        else:
            final_text = native_text
            method = "native"

        page_results.append(PageText(page_number=page_idx + 1, method=method, text=final_text))
        merged.append(f"===== Page {page_idx + 1} ({method}) =====\n{final_text}")

    document = DocumentText(
        pages_total=pages_total,
        pages_ocr=sum(1 for p in page_results if p.method == "ocr"),
        text="\n\n".join(merged).strip(),
    )
    return document, page_results
