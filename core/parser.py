from pathlib import Path
from typing import Optional, Tuple

import bs4  # type: ignore
import markdown  # type: ignore
from langdetect import detect  # type: ignore


def _try_pdf_text(path: Path) -> Optional[str]:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(texts)
    except Exception:
        return None


def _parse_html(raw: bytes) -> str:
    soup = bs4.BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator="\n")


def _parse_docx(path: Path) -> Optional[str]:
    try:
        import docx  # type: ignore

        doc = docx.Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return None


def _parse_markdown(raw: bytes) -> str:
    try:
        html = markdown.markdown(raw.decode("utf-8", errors="ignore"))
        return _parse_html(html.encode("utf-8"))
    except Exception:
        return raw.decode("utf-8", errors="ignore")


def parse_text(path: str, mime_type: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Rich parser: txt/md/html/pdf/docx supported; falls back to utf-8 decode.
    Returns (text, language_guess).
    """
    p = Path(path)
    raw = p.read_bytes()
    lower_mime = mime_type.lower() if mime_type else None
    suffix = p.suffix.lower()
    text = raw.decode("utf-8", errors="ignore")
    if lower_mime in {"text/plain"} or suffix in {".txt"}:
        text = raw.decode("utf-8", errors="ignore")
    elif lower_mime in {"text/markdown"} or suffix in {".md", ".markdown"}:
        text = _parse_markdown(raw)
    elif lower_mime == "text/html" or suffix == ".html":
        text = _parse_html(raw)
    elif lower_mime == "application/pdf" or suffix == ".pdf":
        txt = _try_pdf_text(p)
        if txt:
            text = txt
    elif lower_mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or suffix == ".docx":
        txt = _parse_docx(p)
        if txt:
            text = txt
    lang = None
    try:
        lang = detect(text[:1000]) if text else None
    except Exception:
        lang = None
    return text, lang
