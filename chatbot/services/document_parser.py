"""
Document & Image Text Extraction Service.
Supports PDF, DOCX, TXT, JPG, JPEG, and PNG.
"""

import os
import io
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    'pdf': 'PDF Document',
    'docx': 'Word Document',
    'txt': 'Text File',
    'jpg': 'JPEG Image',
    'jpeg': 'JPEG Image',
    'png': 'PNG Image',
}

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_EXTRACTED_CHARS = 45000  # Safe limit for context window


def _configure_tesseract():
    """Attempts to discover and configure tesseract executable if on Windows."""
    try:
        import pytesseract
        # If already configured and working, return
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for path in common_paths:
            if os.path.isfile(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
    except Exception as exc:
        logger.debug("Tesseract path auto-detection skipped: %s", exc)


def extract_text_from_file(file_obj, filename: str) -> Dict[str, Any]:
    """
    Extracts text from an uploaded file object (InMemoryUploadedFile or TemporaryUploadedFile).
    Returns a dict with:
      - success (bool)
      - filename (str)
      - file_type (str)
      - file_size (int)
      - extracted_text (str)
      - word_count (int)
      - char_count (int)
      - note (str)
      - error (str or None)
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            'success': False,
            'error': f"Unsupported file type '.{ext}'. Supported formats: PDF, DOCX, TXT, JPG, JPEG, PNG.",
            'filename': filename,
            'extracted_text': '',
        }

    file_bytes = file_obj.read()
    file_size = len(file_bytes)

    if file_size > MAX_FILE_SIZE_BYTES:
        return {
            'success': False,
            'error': f"File exceeds maximum allowed size of 20MB (received {file_size / (1024*1024):.1f}MB).",
            'filename': filename,
            'extracted_text': '',
        }

    extracted_text = ""
    note = ""

    try:
        if ext == 'txt':
            for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
                try:
                    extracted_text = file_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

        elif ext == 'pdf':
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            total_pages = len(pdf_reader.pages)
            page_texts = []
            for i, page in enumerate(pdf_reader.pages):
                page_txt = page.extract_text() or ""
                if page_txt.strip():
                    page_texts.append(f"--- Page {i + 1} ---\n{page_txt.strip()}")
            
            extracted_text = "\n\n".join(page_texts)
            note = f"Extracted from {total_pages} pages."
            if not extracted_text.strip():
                extracted_text = "[Notice: This PDF contains scanned images or non-selectable text without embedded text layer.]"

        elif ext == 'docx':
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            
            # Also extract text from tables
            table_texts = []
            for table in doc.tables:
                for row in table.rows:
                    row_txt = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_txt:
                        table_texts.append(row_txt)
            
            all_text_parts = paragraphs
            if table_texts:
                all_text_parts.append("\n[Tables Content]:\n" + "\n".join(table_texts))
            
            extracted_text = "\n\n".join(all_text_parts)
            note = f"Extracted {len(paragraphs)} paragraphs and {len(doc.tables)} tables."

        elif ext in ('jpg', 'jpeg', 'png'):
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            width, height = img.size
            img_format = img.format or ext.upper()
            
            _configure_tesseract()
            ocr_text = ""
            ocr_attempted = False
            try:
                import pytesseract
                ocr_attempted = True
                # Convert to RGB if needed
                if img.mode not in ('L', 'RGB'):
                    img_to_ocr = img.convert('RGB')
                else:
                    img_to_ocr = img
                ocr_text = pytesseract.image_to_string(img_to_ocr).strip()
            except Exception as ocr_err:
                logger.info("OCR execution note: %s", ocr_err)
                note = f"Image {width}x{height}px ({img_format}). Note: Tesseract OCR binary not detected on system PATH."

            if ocr_text:
                extracted_text = ocr_text
                note = f"OCR extracted from image ({width}x{height}px)."
            else:
                if not note:
                    note = f"Image metadata: {width}x{height}px, {img_format} mode {img.mode}."
                extracted_text = f"[Image Document: {filename} ({width}x{height} pixels, format {img_format}). {note}]"

    except Exception as exc:
        logger.exception("Error extracting text from file %s: %s", filename, exc)
        return {
            'success': False,
            'error': f"Failed to extract document contents: {str(exc)}",
            'filename': filename,
            'extracted_text': '',
        }

    # Clean and truncate if needed
    cleaned_text = extracted_text.strip()
    is_truncated = False
    if len(cleaned_text) > MAX_EXTRACTED_CHARS:
        cleaned_text = cleaned_text[:MAX_EXTRACTED_CHARS] + f"\n\n... [Content truncated at {MAX_EXTRACTED_CHARS} characters for optimal processing] ..."
        is_truncated = True

    words = len(cleaned_text.split()) if cleaned_text else 0

    return {
        'success': True,
        'filename': filename,
        'file_type': ext,
        'file_size': file_size,
        'extracted_text': cleaned_text,
        'word_count': words,
        'char_count': len(cleaned_text),
        'truncated': is_truncated,
        'note': note,
        'error': None,
    }
