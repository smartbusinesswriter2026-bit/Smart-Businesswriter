"""Document text extraction for attached PDFs and images (B-107).

The reader is **optional and fail-closed**:

* PDF **text layer** extraction uses ``pypdf`` when it is installed.  A PDF with no text
  layer (a scan) is rendered with ``pypdfium2`` and read by a local Tesseract, or — when
  no Tesseract is installed — by a configured vision model (:mod:`bp.product.ocr`);
  otherwise it is reported as ``ocr_required`` naming what is missing.  Text is never guessed.
* Image OCR uses ``pytesseract`` plus a local Tesseract binary when both are installed, and
  otherwise the configured vision model.  With neither, the file is reported as
  ``ocr_required``.  The engine that read a page is recorded, never implied.
* OCR is capped at 20 pages (rendering every page is slow); the text-layer route is capped
  at 50 pages and 200,000 characters.  Encrypted PDFs are refused.

Limits are refused, not truncated.  The extracted text is **unverified**: it must be checked
against the document by the user.  Nothing here imports the frozen method library or computes
a business number.
"""

import importlib.util
import io
import os
import re
import shutil

from . import ocr as ocr_model

MAX_PAGES = 50
MAX_OCR_PAGES = 20
MAX_CHARS = 200_000
MIN_CHARS = 5
RENDER_SCALE = 2.0   # about 144 dpi, enough for body text and kind to CPU time

_TESSERACT = None


class DocumentError(Exception):
    """The document cannot be read; the message says why."""


def pypdf_available():
    return importlib.util.find_spec("pypdf") is not None


def pdf_renderer_available():
    return importlib.util.find_spec("pypdfium2") is not None


def _tesseract_cmd():
    """The local Tesseract binary: an explicit env var, PATH, then the usual Windows locations."""
    global _TESSERACT
    if _TESSERACT is not None: return _TESSERACT or None
    candidates = [os.environ.get("BP_TESSERACT_CMD"), shutil.which("tesseract"),
                  r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe")]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            _TESSERACT = candidate; return candidate
    _TESSERACT = ""; return None


def ocr_available():
    return (_tesseract_cmd() is not None
            and importlib.util.find_spec("pytesseract") is not None
            and importlib.util.find_spec("PIL") is not None)


def pdf_ocr_available():
    return ocr_available() and pdf_renderer_available()


def _pytesseract():
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()
    return pytesseract


def _ocr_image(image):
    text = _pytesseract().image_to_string(image) or ""
    return _clean(text)


def _clean(text):
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def extract_pdf(raw):
    """Extract the text layer of a PDF.  Returns a status dictionary, never invented text."""
    if not pypdf_available():
        raise DocumentError("PDF text extraction needs the optional 'pypdf' package; install it, or save the document as CSV/TSV/TXT")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
    except Exception as exc:
        raise DocumentError("this file could not be opened as a PDF (%s)" % type(exc).__name__)
    if getattr(reader, "is_encrypted", False):
        raise DocumentError("the PDF is encrypted; remove the password and attach it again")
    try:
        pages = len(reader.pages)
    except Exception:
        raise DocumentError("the PDF page count could not be read")
    if pages > MAX_PAGES:
        raise DocumentError("the PDF has %d pages; the limit is %d, so split it first" % (pages, MAX_PAGES))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    text = _clean("\n".join(parts))
    if len(text) < MIN_CHARS:
        if pdf_renderer_available() and (pdf_ocr_available() or ocr_model.available()):
            return _ocr_pdf(raw, pages)
        if not pdf_renderer_available():
            reason = ("the PDF has no usable text layer (it looks scanned); rendering its pages "
                      "needs the optional 'pypdfium2' package")
        else:
            reason = ("the PDF has no usable text layer (it looks scanned); OCR needs a local "
                      "Tesseract or a configured OCR model (BP_OCR_MODEL), and neither is available")
        return {"status": "ocr_required", "pages": pages, "chars": len(text), "reason": reason}
    if len(text) > MAX_CHARS:
        raise DocumentError("the extracted text is longer than the %d-character limit; split the document" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": pages, "chars": len(text), "method": "pdf_text_layer"}


def _ocr_pdf(raw, pages):
    """Render a scanned PDF with pdfium and read each page with the best engine available.

    A local Tesseract is preferred because it is free and offline; the vision model is
    used when no Tesseract is installed, and its name is recorded on the result so the
    student can see what read their document.
    """
    if pages > MAX_OCR_PAGES:
        raise DocumentError("the scanned PDF has %d pages; OCR is limited to %d, so split it first" % (pages, MAX_OCR_PAGES))
    use_model = ocr_model.available() and not pdf_ocr_available()
    try:
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(raw)
    except Exception as exc:
        raise DocumentError("this PDF could not be rendered for OCR (%s)" % type(exc).__name__)
    parts = []
    try:
        for index in range(pages):
            page = document[index]
            try:
                bitmap = page.render(scale=RENDER_SCALE)
                try:
                    if use_model:
                        buffer = io.BytesIO()
                        bitmap.to_pil().save(buffer, format="PNG")
                        try:
                            parts.append(_clean(ocr_model.read(buffer.getvalue(), "image/png")))
                        except ocr_model.OcrError as error:
                            raise DocumentError("page %d could not be read: %s" % (index + 1, error))
                    else:
                        parts.append(_ocr_image(bitmap.to_pil()))
                finally:
                    bitmap.close()
            finally:
                page.close()
    finally:
        document.close()
    text = _clean("\n".join(parts))
    if len(text) < MIN_CHARS:
        return {"status": "ocr_required", "pages": pages, "chars": len(text),
                "reason": "OCR ran but found no usable text in this PDF"}
    if len(text) > MAX_CHARS:
        raise DocumentError("the OCR text is longer than the %d-character limit; split the document" % MAX_CHARS)
    if use_model:
        return {"status": "extracted", "text": text, "pages": pages, "chars": len(text),
                "method": "pdf_ocr_model", "engine": ocr_model.model_id()}
    return {"status": "extracted", "text": text, "pages": pages, "chars": len(text), "method": "pdf_ocr"}


def _model_image(raw, ext):
    """Read one image with the configured vision model."""
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else (
        "image/webp" if ext == ".webp" else "image/png")
    try:
        text = _clean(ocr_model.read(raw, mime))
    except ocr_model.OcrError as error:
        raise DocumentError(str(error))
    if len(text) < MIN_CHARS:
        return {"status": "ocr_required", "pages": 1, "chars": len(text),
                "reason": "the OCR model read no usable text from this image"}
    if len(text) > MAX_CHARS:
        raise DocumentError("the extracted text is longer than the %d-character limit" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": 1, "chars": len(text),
            "method": "image_ocr_model", "engine": ocr_model.model_id()}


def extract_image(raw, ext):
    """Read one image: the local Tesseract first, then the vision model, else say so."""
    if not ocr_available():
        if ocr_model.available():
            return _model_image(raw, ext)
        return {"status": "ocr_required", "pages": 1, "chars": 0,
                "reason": "image OCR needs Tesseract and 'pytesseract' on this machine, or a "
                          "configured OCR model (BP_OCR_MODEL); install Tesseract, or paste the text yourself"}
    try:
        from PIL import Image
        text = _ocr_image(Image.open(io.BytesIO(raw)))
    except Exception as exc:
        raise DocumentError("the image could not be read (%s)" % type(exc).__name__)
    if len(text) < 5:
        return {"status": "ocr_required", "pages": 1, "chars": len(text),
                "reason": "the OCR engine found no usable text in this image"}
    if len(text) > MAX_CHARS:
        raise DocumentError("the extracted text is longer than the %d-character limit" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": 1, "chars": len(text), "method": "image_ocr"}


def extract_docx(raw):
    """The text of a Word .docx, read from its document XML (standard library only).

    Paragraphs become lines; tabs and explicit breaks are kept as whitespace.
    Comments, headers and tracked deletions are not included.  An empty document
    is refused rather than reported as a successful extraction.
    """
    import zipfile
    from xml.etree import ElementTree
    if not raw or raw[:2] != b"PK":
        raise DocumentError("this file is not a Word .docx document")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, OSError) as exc:
        raise DocumentError("this .docx could not be opened (%s)" % type(exc).__name__)
    with archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            raise DocumentError("this .docx has no word/document.xml part, so it is not a Word text document")
        try:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        except (ElementTree.ParseError, KeyError) as exc:
            raise DocumentError("this .docx document XML could not be read (%s)" % type(exc).__name__)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    parts = []
    for paragraph in root.iter(ns + "p"):
        pieces = []
        for node in paragraph.iter():
            if node.tag == ns + "t":
                pieces.append(node.text or "")
            elif node.tag == ns + "tab":
                pieces.append(" ")
            elif node.tag in (ns + "br", ns + "cr"):
                pieces.append("\n")
        line = _clean("".join(pieces))
        if line:
            parts.append(line)
    text = _clean("\n".join(parts))
    if len(text) < MIN_CHARS:
        raise DocumentError("the Word document contains no readable text; copy the text into the brief instead")
    if len(text) > MAX_CHARS:
        raise DocumentError("the extracted text is longer than the %d-character limit; split the document" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": None, "chars": len(text), "method": "docx_text"}


def extract_txt(raw):
    """A plain-text brief.  UTF-8, UTF-16 with a BOM and Windows-1252 are tried, in that order."""
    if not raw:
        raise DocumentError("the text file is empty")
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        candidates = ["utf-16"]
    elif raw[:3] == b"\xef\xbb\xbf":
        candidates = ["utf-8-sig", "cp1252"]
    else:
        candidates = ["utf-8", "cp1252"]
    text = None
    for encoding in candidates:
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise DocumentError("the text file is not readable as UTF-8 or Windows-1252")
    if "\x00" in text:
        raise DocumentError("the text file contains binary data, not text")
    text = _clean(text)
    if len(text) < MIN_CHARS:
        raise DocumentError("the text file is empty or too short to be a brief")
    if len(text) > MAX_CHARS:
        raise DocumentError("the text is longer than the %d-character limit; split the document" % MAX_CHARS)
    return {"status": "extracted", "text": text, "pages": None, "chars": len(text), "method": "text_file"}


def extract_document(raw, filename):
    """Read a brief attachment by its declared extension.  Text is never guessed."""
    ext = os.path.splitext(str(filename or ""))[1].lower()
    if ext == ".pdf":
        return extract_pdf(raw)
    if ext in (".docx", ".docm"):
        return extract_docx(raw)
    if ext in (".txt", ".text", ".md"):
        return extract_txt(raw)
    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        return extract_image(raw, ext)
    raise DocumentError("attach a PDF, Word .docx, TXT, PNG or JPG file, or paste the brief as text")
