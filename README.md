# PDF OCR Extractor (Python + UI)

Проект распознает текст в PDF:
- сначала извлекает встроенный текст (быстро),
- если страница пустая/плохого качества, включает OCR,
- работает с обычными и старыми сканами.

## Требования

- Python 3.10+
- Tesseract OCR
- Языковые пакеты Tesseract для `rus` и `eng`

Проверка:

```bash
tesseract --version
tesseract --list-langs
```

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Запуск UI

```bash
source .venv/bin/activate
streamlit run app.py
```

Откройте адрес, который покажет Streamlit (обычно `http://localhost:8501`).

## Настройки через переменные окружения

```bash
export OCR_LANG="rus+eng"
export OCR_DPI="300"
export MIN_NATIVE_CHARS="60"
export OCR_MAX_WORKERS="4"
```

## Как работает

1. Постранично пробует извлечь текст через `pypdf`.
2. Если текста мало, рендерит страницу в изображение (`pypdfium2`).
3. Запускает OCR (`pytesseract`) на нескольких вариантах предобработки (`opencv`).
4. Выбирает лучший результат и выводит единый текст документа в UI.
