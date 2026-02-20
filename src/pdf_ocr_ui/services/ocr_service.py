from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pypdfium2 as pdfium
import pytesseract
from PIL import Image

from pdf_ocr_ui.settings import OCRSettings


@dataclass(slots=True)
class OCRCandidate:
    text: str
    confidence: float


def _to_grayscale(np_image: np.ndarray) -> np.ndarray:
    if np_image.ndim == 2:
        return np_image
    return cv2.cvtColor(np_image, cv2.COLOR_BGR2GRAY)


def _denoise(np_image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(np_image, None, h=18, templateWindowSize=7, searchWindowSize=21)


def _adaptive_binary(np_image: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        np_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        51,
        11,
    )


def _otsu_binary(np_image: np.ndarray) -> np.ndarray:
    _, th = cv2.threshold(np_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th


def _score_candidate(image: np.ndarray, language: str, config: str) -> OCRCandidate:
    data = pytesseract.image_to_data(image, lang=language, config=config, output_type=pytesseract.Output.DICT)
    confidences: list[float] = []
    words: list[str] = []

    for conf_raw, token in zip(data["conf"], data["text"]):
        token = token.strip()
        if not token:
            continue
        try:
            conf = float(conf_raw)
        except (TypeError, ValueError):
            continue
        if conf > 0:
            confidences.append(conf)
            words.append(token)

    if not words:
        return OCRCandidate(text="", confidence=0.0)

    avg_conf = sum(confidences) / max(len(confidences), 1)
    return OCRCandidate(text=" ".join(words), confidence=avg_conf)


def _best_ocr_text(np_image: np.ndarray, settings: OCRSettings) -> str:
    gray = _to_grayscale(np_image)
    denoised = _denoise(gray)

    variants = [
        denoised,
        _adaptive_binary(denoised),
        _otsu_binary(denoised),
    ]

    # PSM 6 is robust for dense blocks, PSM 11 works better for sparse old scans.
    configs = ["--oem 3 --psm 6", "--oem 3 --psm 11"]

    best = OCRCandidate(text="", confidence=0.0)
    for variant in variants:
        for config in configs:
            candidate = _score_candidate(variant, settings.language, config)
            if candidate.confidence > best.confidence and len(candidate.text) > len(best.text) * 0.7:
                best = candidate

    return best.text


def render_page_to_image(pdf_bytes: bytes, page_index: int, settings: OCRSettings) -> np.ndarray:
    doc = pdfium.PdfDocument(pdf_bytes)
    page = doc[page_index]
    scale = settings.render_dpi / 72
    bitmap = page.render(scale=scale)
    pil_image = bitmap.to_pil()
    np_img = np.array(pil_image)
    return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)


def ocr_page(pdf_bytes: bytes, page_index: int, settings: OCRSettings) -> str:
    image = render_page_to_image(pdf_bytes, page_index, settings)
    return _best_ocr_text(image, settings)


def ocr_image(np_image: np.ndarray, settings: OCRSettings) -> str:
    return _best_ocr_text(np_image, settings)
