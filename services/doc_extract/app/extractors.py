import os
from typing import Tuple
from PIL import Image
from paddleocr import PaddleOCR
from docling.document_converter import DocumentConverter

# OCR engine (English only per your requirement)
_OCR = PaddleOCR(use_angle_cls=True, lang="en")

def ocr_image(image_path: str) -> str:
    result = _OCR.ocr(image_path, cls=True)
    lines = []
    for page in result:
        for item in page:
            text = item[1][0]
            lines.append(text)
    return "\n".join(lines)

def extract_pdf_with_docling(pdf_path: str) -> str:
    # Docling converts PDF to structured document; we use text output for LLM structuring
    converter = DocumentConverter()
    doc = converter.convert(pdf_path).document
    # keep it simple: extract plain text (tables also represented)
    return doc.export_to_markdown()

def extract_text(file_path: str, mime_type: str) -> Tuple[str, str]:
    """
    Returns (text, method)
    """
    if mime_type in ("image/png","image/jpeg","image/jpg","image/webp"):
        return ocr_image(file_path), "paddleocr"
    if mime_type in ("application/pdf",):
        try:
            return extract_pdf_with_docling(file_path), "docling"
        except Exception:
            # fallback: convert PDF pages to images could be added later;
            # for now just raise
            raise
    raise ValueError(f"Unsupported mime_type: {mime_type}")
