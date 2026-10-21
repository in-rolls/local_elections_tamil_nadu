"""Recover Unicode Tamil from the commission's result PDFs.

Neither PDF family yields correct Tamil from ordinary text extraction.

2019 and 2021 (mPDF 5.7.4, font ind_ta_1_001, Identity-H). mPDF writes each
character's own code point as its glyph code, except that it first moves the
pre-base vowel signs (ெ ே ை) in front of their consonant and then replaces
conjuncts and consonant+vowel ligatures with Private Use Area codes using the
font's substitution table, includes/ind_ta_1_001.volt.php in mPDF v5.7.4
(vendored as data/reference/ind_ta_1_001.volt.php). `mpdf()` undoes both
steps: each PUA code is replaced by the sequence its rule matched, and each
pre-base vowel is moved back after the unit that follows it.

2011 (Windows PostScript driver, then Ghostscript 8.15). Each district file
embeds subsets of the Latha font. The PDF encoding names each glyph either by
code point (u0B95, uni0B95, uni0B95_uni0BC1 for a ligature, uni0BBF.psts for
a positional variant), by Adobe name (space, one) or by bare glyph index (g132)
or a private name (tm_ra_halant). Bare indices and private names were read off
the glyph outlines embedded in the files (rendered 2026-10-18; LATHA below).
Glyphs keep visual order, so pre-base vowels are moved back as for mPDF.
"""

import re
import unicodedata
from pathlib import Path

from pdfminer import pdffont
from pdfminer.psparser import literal_name

from local_elections_tamil_nadu.collect.fetch import ROOT

VOLT = ROOT / "data" / "reference" / "ind_ta_1_001.volt.php"
PRE = "ெேை"
CONSONANTS = {chr(c) for c in range(0x0B95, 0x0BBA)}
TWO_PART = {
    "ொ": "ொ",
    "ோ": "ோ",
    "ௌ": "ௌ",
}
PULLI = "்"
VI, VII, VU, VUU = "ி", "ீ", "ு", "ூ"

# Latha glyphs named by bare index in the 2011 files, read from their outlines.
LATHA = {
    "g116": "க" + PULLI,
    "g117": "ங" + PULLI,
    "g118": "ச" + PULLI,
    "g119": "ஜ" + PULLI,
    "g120": "ஞ" + PULLI,
    "g121": "ட" + PULLI,
    "g122": "ண" + PULLI,
    "g123": "த" + PULLI,
    "g124": "ந" + PULLI,
    "g125": "ன" + PULLI,
    "g126": "ப" + PULLI,
    "g127": "ம" + PULLI,
    "g128": "ய" + PULLI,
    "g129": "ர" + PULLI,
    "g130": "ற" + PULLI,
    "g131": "ல" + PULLI,
    "g132": "ள" + PULLI,
    "g133": "ழ" + PULLI,
    "g134": "வ" + PULLI,
    "g135": "ஷ" + PULLI,
    "g136": "ஸ" + PULLI,
    "g137": "ஹ" + PULLI,
    "g138": "க" + PULLI + "ஷ" + PULLI,
    "g142": VI,
    "g143": VI,
    "g145": VII,
    "g146": VII,
    "g147": VII,  # zero-width ring drawn over the consonant
    "g148": "க" + VU,
    "g149": "க" + VUU,
    "g152": "ச" + VU,
    "g153": "ச" + VUU,
    "g156": "ட" + VI,
    "g157": "ட" + VII,
    "g158": "ட" + VU,
    "g159": "ட" + VUU,
    "g160": "ண" + VU,
    "g161": "ண" + VUU,
    "g162": "த" + VU,
    "g163": "த" + VUU,
    "g164": "ந" + VU,
    "g165": "ந" + VUU,
    "g167": "ன" + VU,
    "g168": "ன" + VUU,
    "g169": "ப" + VU,
    "g170": "ப" + VUU,
    "g171": "ம" + VU,
    "g172": "ம" + VUU,
    "g173": "ய" + VU,
    "g174": "ய" + VUU,
    "g175": "ர" + VU,
    "g176": "ர" + VUU,
    "g178": "ற" + VU,
    "g179": "ற" + VUU,
    "g180": "ல" + VU,
    "g181": "ல" + VUU,
    "g182": "ள" + VU,
    "g183": "ள" + VUU,
    "g184": "ழ" + VU,
    "g185": "ழ" + VUU,
    "g186": "வ" + VU,
    "g187": "வ" + VUU,
    "g188": "ஸ" + PULLI + "ர" + VII,
    "g190": "ர" + VI,
    "g191": "ர" + VII,
    "g192": "",  # dotted circle placeholder
    "glyph189": VII,  # same outline as g147, in the other Latha build
    "tm_ra_halant": "ர" + PULLI,
    "tm_r_ikaar": "ர" + VI,
    "tm_r_iikaar": "ர" + VII,
    "tm_l_iikaar": "ல" + VII,
}
UNI = re.compile(r"(?:uni|u)([0-9A-F]{4})")


def glyph_text(name):
    """Unicode for one 2011 glyph name, or None if the name is unknown."""
    if name in LATHA:
        return LATHA[name]
    base = name.split(".", 1)[0]
    parts = base.split("_")
    if all(UNI.fullmatch(p) for p in parts):
        return "".join(chr(int(UNI.fullmatch(p).group(1), 16)) for p in parts)
    return None


def _install():
    """Make pdfminer report 2011 Tamil glyphs by name instead of ToUnicode.

    The ToUnicode maps in these files send ligature glyphs to nothing or to
    the wrong code, so for any glyph whose encoding name glyph_text() knows,
    the name wins. Unknown names become ⟦name⟧ so that they stay visible.
    """
    if getattr(pdffont.PDFSimpleFont, "_tamil", False):
        return
    init, to_unichr = pdffont.PDFSimpleFont.__init__, pdffont.PDFSimpleFont.to_unichr

    def patched_init(self, descriptor, widths, spec):
        init(self, descriptor, widths, spec)
        self._names = {}
        enc = pdffont.resolve1(spec.get("Encoding"))
        if isinstance(enc, dict):
            code = None
            for d in pdffont.list_value(enc.get("Differences", [])):
                if isinstance(d, int):
                    code = d
                else:
                    self._names[code] = literal_name(d)
                    code += 1

    def patched_to_unichr(self, cid):
        name = getattr(self, "_names", {}).get(cid)
        if name is not None and re.match(r"(g\d|glyph\d|tm_|u0B|uni0B)", name):
            text = glyph_text(name)
            return f"⟦{name}⟧" if text is None else text
        return to_unichr(self, cid)

    pdffont.PDFSimpleFont.__init__ = patched_init
    pdffont.PDFSimpleFont.to_unichr = patched_to_unichr
    pdffont.PDFSimpleFont._tamil = True


_install()


def _volt():
    src = Path(VOLT).read_text(encoding="utf-8")
    table = {}
    for match, repl in re.findall(
        r"'match' => '([^']*)',\s*'replace' => '([^']*)'", src
    ):
        pua = [t for t in repl.split() if re.fullmatch(r"E0[0-9A-F]{2}", t)]
        if not pua:
            continue
        # "(X) Y -> \1 PUA": X is kept, so PUA stands for Y alone.
        rest = re.sub(r"^\(+.*?\)+\s*", "", match) if "1" in repl.split()[0] else match
        seq = "".join(
            chr(int(t, 16)) for t in rest.split() if t not in ("200C", "200D")
        )
        if table.setdefault(chr(int(pua[0], 16)), seq) != seq:
            raise ValueError(f"PUA {pua[0]} maps to two sequences")
    return table


PUA = _volt()


def reorder(text):
    """Move each pre-base vowel sign back after the unit that follows it."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c in PRE and i + 1 < len(text) and text[i + 1] not in PRE + " ":
            out += [text[i + 1], c]
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def finish(text):
    text = text.replace("\u25cc", "")  # dotted-circle placeholder glyph
    # a vowel sign or pulli never starts a word: a space before one comes from
    # a separately drawn sign, not from the source
    text = re.sub(r"\s+([\u0bbe-\u0bcd\u0bd7])", r"\1", text)
    for a, b in TWO_PART.items():
        text = text.replace(a, b)
    return unicodedata.normalize("NFC", text)


def mpdf(text):
    """2019/2021: undo mPDF's reordering and PUA substitution."""
    text = reorder(text)
    return finish("".join(PUA.get(c, c) for c in text))


def latha(text):
    """2011: text already mapped glyph-by-glyph; restore logical order."""
    return finish(reorder(text))
