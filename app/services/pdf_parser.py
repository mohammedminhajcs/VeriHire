from __future__ import annotations

from io import BytesIO


MIN_TEXT_LENGTH = 80


# Extracts text using embedded PDF text layer when available.
def _extract_text_layer(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("pypdf is not installed. Install dependencies from requirements.txt.") from error

    reader = PdfReader(BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


# Runs OCR over rendered PDF pages when text-layer extraction is insufficient.
def _extract_text_with_ocr(file_bytes: bytes, page_limit: int = 4) -> str:
    try:
        import fitz
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return ""

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return ""

    engine = RapidOCR()
    collected: list[str] = []

    for index, page in enumerate(document):
        if index >= page_limit:
            break

        # Upscale render slightly to improve OCR quality.
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        result, _ = engine(image)
        if result:
            collected.append(" ".join(item[1] for item in result if len(item) >= 2))

    return "\n".join(collected).strip()


# Extracts plain text from an uploaded PDF using pypdf.
def extract_text_from_pdf(file_bytes: bytes) -> str:
    text, _ = extract_text_with_source(file_bytes)
    return text


# Extracts text and indicates whether text layer or OCR was used.
def extract_text_with_source(file_bytes: bytes) -> tuple[str, str]:
    text = _extract_text_layer(file_bytes)
    if len(text) >= MIN_TEXT_LENGTH:
        return text, "pdf_text"

    ocr_text = _extract_text_with_ocr(file_bytes)
    if len(ocr_text) >= max(40, len(text)):
        if text:
            return f"{text}\n{ocr_text}".strip(), "pdf_ocr"
        return ocr_text, "pdf_ocr"

    return text, "pdf_text"