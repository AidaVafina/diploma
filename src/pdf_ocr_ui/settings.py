from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OCRSettings:
    language: str = os.getenv("OCR_LANG", "rus+eng")
    render_dpi: int = int(os.getenv("OCR_DPI", "300"))
    min_native_chars: int = int(os.getenv("MIN_NATIVE_CHARS", "60"))
    max_workers: int = int(os.getenv("OCR_MAX_WORKERS", "4"))


DEFAULT_SETTINGS = OCRSettings()
