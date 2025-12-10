# parsers/resume_parser.py
import os
import tempfile
from typing import Dict
import pdfplumber
import docx2txt

def parse_resume_file(file_bytes: bytes, filename: str) -> Dict:
    """
    Saves file temporarily and extracts raw_text.
    Returns { "raw_text": str, "sections": {...} }
    """
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1])
    os.close(fd)
    with open(path, "wb") as f:
        f.write(file_bytes)

    ext = filename.lower().split(".")[-1]
    text = ""
    try:
        if ext == "pdf":
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\n".join(pages)
        elif ext in ("doc", "docx"):
            text = docx2txt.process(path)
        else:
            text = open(path, "r", encoding="utf-8", errors="ignore").read()
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

    # naive sectioning: split by common headings
    sections = {}
    markers = ["experience", "work experience", "professional experience", "education", "skills", "projects", "summary"]
    lower = text.lower()
    for m in markers:
        idx = lower.find(m)
        if idx != -1:
            # crude extraction: next 400 chars
            sections[m] = text[idx: idx + 800]
    return {"raw_text": text, "sections": sections}
