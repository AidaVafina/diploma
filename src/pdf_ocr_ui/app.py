from __future__ import annotations

import json
import pytesseract
import streamlit as st

from pdf_ocr_ui.services.pdf_service import extract_text_from_pdf
from pdf_ocr_ui.settings import DEFAULT_SETTINGS, OCRSettings


@st.cache_resource
def get_settings() -> OCRSettings:
    return DEFAULT_SETTINGS


def main() -> None:
    st.set_page_config(page_title="PDF OCR Extractor", page_icon="📄", layout="wide")

    st.title("PDF OCR Extractor")
    st.caption("Извлекает текст из PDF и автоматически применяет OCR для сканов и старых документов.")

    with st.expander("Настройки OCR", expanded=False):
        st.write("Язык:", get_settings().language)
        st.write("DPI рендера:", get_settings().render_dpi)
        st.write("Минимум символов для native-текста:", get_settings().min_native_chars)

    uploaded = st.file_uploader("Загрузите PDF", type=["pdf"])

    if not uploaded:
        st.info("Выберите файл PDF для обработки.")
        return

    if st.button("Обработать", type="primary"):
        tesseract_path = pytesseract.pytesseract.tesseract_cmd
        st.write(f"Tesseract: `{tesseract_path}`")

        with st.spinner("Сканирование документа..."):
            pdf_bytes = uploaded.getvalue()
            document, pages, articles = extract_text_from_pdf(pdf_bytes, get_settings())

        st.success("Готово")
        c1, c2, c3 = st.columns(3)
        c1.metric("Всего страниц", document.pages_total)
        c2.metric("Страниц через OCR", document.pages_ocr)
        c3.metric("Статей", len(articles))

        if document.orthography:
            label = "дореформенная" if document.orthography.pre_reform else "современная"
            st.write(f"Орфография: {label}")

        st.subheader("Текст документа")
        st.text_area("Результат", value=document.text, height=500)

        st.download_button(
            label="Скачать TXT",
            data=document.text.encode("utf-8"),
            file_name=f"{uploaded.name.rsplit('.', 1)[0]}_extracted.txt",
            mime="text/plain",
        )

        if document.modern_text:
            st.subheader("Текст после преобразования")
            st.text_area(
                "Результат (современная орфография)",
                value=document.modern_text,
                height=500,
            )
            st.download_button(
                label="Скачать TXT (современная орфография)",
                data=document.modern_text.encode("utf-8"),
                file_name=f"{uploaded.name.rsplit('.', 1)[0]}_modern.txt",
                mime="text/plain",
            )

        if articles:
            st.subheader("Статьи")
            with st.expander("Список статей", expanded=False):
                for article in articles:
                    st.write(
                        f"#{article.article_id} — {article.title} "
                        f"(стр. {article.page_start}-{article.page_end})"
                    )

            articles_payload = [
                {
                    "article_id": a.article_id,
                    "title": a.title,
                    "page_start": a.page_start,
                    "page_end": a.page_end,
                    "text": a.text,
                }
                for a in articles
            ]
            st.download_button(
                label="Скачать статьи (JSON)",
                data=json.dumps(articles_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{uploaded.name.rsplit('.', 1)[0]}_articles.json",
                mime="application/json",
            )

        with st.expander("Постраничная диагностика", expanded=False):
            for page in pages:
                st.write(f"Страница {page.page_number}: {page.method}, символов: {len(page.text)}")


if __name__ == "__main__":
    main()
