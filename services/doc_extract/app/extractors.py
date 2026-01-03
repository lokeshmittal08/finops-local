import re
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
import cv2
import numpy as np
from PIL import Image

def _preprocess_for_ocr(pil_img: Image.Image) -> Image.Image:
    # Convert to grayscale + adaptive threshold (helps bank statement scans a lot)
    img = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)  # denoise but keep edges
    thr = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
    )
    return Image.fromarray(thr)

def _tesseract(img: Image.Image) -> str:
    # Good default for statement-like blocks
    config = r'--oem 1 --psm 6'
    return pytesseract.image_to_string(img, lang="eng", config=config)

def _looks_like_real_text(text: str) -> bool:
    # If we extracted real PDF text, we should see enough alphanumerics + multiple lines
    if not text: 
        return False
    stripped = re.sub(r"\s+", " ", text).strip()
    return len(stripped) > 200 and sum(c.isalnum() for c in stripped) > 150

def extract_text(file_path: str, mime_type: str):
    # PDFs
    if mime_type == "application/pdf" or file_path.lower().endswith(".pdf"):
        # 1) Try digital text extraction first (highest accuracy)
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:50]:  # safety cap
                t = page.extract_text() or ""
                text += t + "\n"

        if _looks_like_real_text(text):
            return text, "pdf-text"

        # 2) OCR fallback (scanned PDF)
        doc = fitz.open(file_path)
        out = []
        for i, page in enumerate(doc[:25]):  # cap pages for v1
            pix = page.get_pixmap(dpi=300)
            pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pil = _preprocess_for_ocr(pil)
            out.append(_tesseract(pil))
        return "\n".join(out), "tesseract-ocr"

    # Images
    pil = Image.open(file_path)
    pil = _preprocess_for_ocr(pil)
    return _tesseract(pil), "tesseract-ocr"