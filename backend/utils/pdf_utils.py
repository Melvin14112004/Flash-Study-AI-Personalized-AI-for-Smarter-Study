import logging
import fitz
import pytesseract
from typing import List
from config import MAX_PDF_PAGES

from PIL import Image
import io

# Path to tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

logger = logging.getLogger("pdf_utils")


def clean_text_keep_formulas(text: str) -> str:
    import re
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_text_from_pdf(path: str) -> str:
    logger.info("Extracting PDF text (LIMIT %d pages): %s", MAX_PDF_PAGES, path)

    texts = []

    try:
        doc = fitz.open(path)
        total_pages = doc.page_count
        limit = min(total_pages, MAX_PDF_PAGES)

        # -------------------------------------------
        # PHASE 1: Try normal text extraction
        # -------------------------------------------
        for i in range(limit):
            try:
                page = doc.load_page(i)
                t = page.get_text("text")
                if t and t.strip():
                    texts.append(t)
            except Exception:
                logger.exception("Error reading page %d", i)

        extracted = clean_text_keep_formulas("\n\n".join(texts))

        # -------------------------------------------
        # PHASE 2: OCR fallback if no text extracted
        # -------------------------------------------
        if not extracted.strip():
            logger.warning("No normal text found — switching to OCR mode")

            ocr_texts = []

            for i in range(limit):
                try:
                    page = doc.load_page(i)
                    pix = page.get_pixmap(dpi=200)

                    # Convert pixmap to PNG bytes → PIL image
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes))

                    # OCR
                    text = pytesseract.image_to_string(img)

                    if text.strip():
                        ocr_texts.append(text)

                except Exception:
                    logger.exception("OCR failed on page %d", i)

            return "\n\n".join(ocr_texts)

        return extracted

    except Exception:
        logger.exception("Failed to open PDF")
        return ""
