"""Shared paths and geometry helpers for the result PDFs."""

from pathlib import Path

from pdfplumber.utils.text import extract_text

from local_elections_tamil_nadu.collect.fetch import ROOT
from local_elections_tamil_nadu.parse import tamil_fonts

RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def page_chars(page):
    """The page's glyphs, cleaned for text extraction.

    Bold headings are overprinted several times, sometimes from different font
    objects, so duplicates at nearly the same spot are dropped whatever their
    font. A zero-width glyph (the 2011 ீ ring) is drawn from the right edge of
    the letter it belongs to, which sorting by x can put after the next
    letter; it is moved inside that letter.
    """
    chars = [dict(c) for c in page.dedupe_chars(tolerance=2, extra_attrs=()).chars]
    wide = [c for c in chars if c["x1"] - c["x0"] >= 0.5]
    for c in chars:
        if c["x1"] - c["x0"] >= 0.5:
            continue
        line = [o for o in wide if abs(o["top"] - c["top"]) < 6]
        if line:
            base = min(line, key=lambda o: abs(o["x1"] - c["x0"]))
            # inside the base letter: sorts after it and before the next one
            c["x0"], c["x1"] = (base["x0"] + base["x1"]) / 2, base["x1"]
            c["top"], c["bottom"] = base["top"], base["bottom"]
    return chars


def inside(chars, bbox):
    x0, top, x1, bottom = bbox
    return [
        c
        for c in chars
        if x0 <= (c["x0"] + c["x1"]) / 2 <= x1
        and top <= (c["top"] + c["bottom"]) / 2 <= bottom
    ]


def text_lines(chars, family, y_tolerance=3):
    """Decoded lines of a set of glyphs, top to bottom."""
    if not chars:
        return []
    decode = tamil_fonts.latha if family == "latha" else tamil_fonts.mpdf
    text = extract_text(chars, layout=False, x_tolerance=1.5, y_tolerance=y_tolerance)
    return [decode(line).strip() for line in text.split("\n") if line.strip()]
