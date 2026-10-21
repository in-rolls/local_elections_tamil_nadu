"""Fold Tamil village panchayat names for matching, and read their qualifiers.

A qualifier is a part of a name that tells two panchayats apart when the rest
of the name is the same. Every family stated on either side of a pair must be
stated, equal, on the other side, or the pair is vetoed (`agree`):

  number     revenue-village and section numbers: "25 வேப்பம்பட்டு",
             "எண்.2 கரியமாணிக்கம்", "ஆயக்காரன்புலம் 3", "பெரம்பூர் 1 சேத்தி",
             "கல்யாணபுரம் II சேத்தி"
  series     lettered parts: "தனிச்சியம் ஏ/சி", "ஏனாதி ஏ/பி"
  initials   dotted initials, Tamil or Latin, before or after the name:
             "எஸ்.புதூர்" vs "எம்.புதூர்", "K.சிவஞானபுரம்", "வன்னஞ்சூர்.மோ".
             Compared by consonant class, so "K." = "கே." = "க."
  direction  கிழக்கு / மேற்கு / வடக்கு / தெற்கு anywhere, also fused
             ("வடக்குவெள்ளூர்"), abbreviated in brackets ("(தெ)"), and the
             short forms வட / தென் starting a word ("வடகடப்பந்தாங்கல்")
  position   மேல / கீழ / நடு starting a word (upper, lower, middle)
  size       சின்ன / சிறு (small) and பெரிய (big) starting a word
  age        புது / புதிய (new) and பழைய (old) starting a word

The folded name drops the number, series, initial and direction qualifiers
(the word-start ones stay, since they are fused into the name: "மேலூர்") and
absorbs spelling variation:
  - the commission's keying of ர as ா before ி/ீ and before ் ("மாாியம்மன்");
  - long and short vowels (ீ/ி, ூ/ு, ே/ெ, ோ/ொ);
  - letters that place names spell either way: ண/ன/ந, ள/ழ/ல, ற/ர, ஷ/ஸ/ஜ/ச;
  - a nasal before a consonant typed as any nasal ("ஒட்டன்காடு" = "ஒட்டங்காடு");
  - a second vowel sign left by decoding ("துரவிக்காடுி");
  - a doubled consonant at a word join ("சின்னப்பட்டி" = "சின்னபட்டி");
  - a leading இ before ர or ல ("இராஜபாளையம்" = "ராஜபாளையம்");
  - spaces, dots and brackets.
The length skeleton also drops ா and the pulli; the full skeleton drops
every vowel sign (see `similarity`).
"""

import re
import unicodedata

from rapidfuzz import fuzz

DIRECTIONS = {"கிழக்கு": "E", "மேற்கு": "W", "வடக்கு": "N", "தெற்கு": "S"}
# abbreviations, only inside brackets: "குலமங்கலம் (தெ)"
DIRECTION_ABBREV = {"கி": "E", "மே": "W", "வ": "N", "தெ": "S"}
WORD_START = {
    "position": [("மேல", "upper"), ("கீழ", "lower"), ("நடு", "middle")],
    "size": [("சின்ன", "small"), ("சிறு", "small"), ("பெரிய", "big")],
    "age": [("புதிய", "new"), ("புது", "new"), ("பழைய", "old")],
}
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
SECTION_WORDS = r"பிட்|சேத்தி|பகுதி"
NUMBER = re.compile(
    r"(?:^|(?<=[\s.,(-]))(?:எண்\s*\.?\s*)?"
    r"(\d{1,3}(?=$|[\s.,)\-஀-௿])|(?:I{1,3}|IV|V)(?=$|[\s)]))"
)
SERIES = re.compile(r"(?:^|\s)((?:ஏ|பி|சி|டி)/(?:ஏ|பி|சி|டி))(?=$|\s)")
# An initial: one Tamil syllable or a spelled letter, or one Latin capital,
# followed by a dot.
INITIAL = re.compile(r"(?:^|(?<=[\s.]))([஀-௿]{1,4}|[A-Z])\s*\.")
# a short syllable after a final dot: "வன்னஞ்சூர்.மோ", "கொளத்தூர்.எ"
TRAILING_INITIAL = re.compile(r"\.\s*([஀-௿]{1,3})\s*$")
# Letter names typed in Tamil for Latin initials, mapped to a consonant class.
LETTER_NAMES = {
    "எஸ்": "ச",
    "எம்": "ம",
    "எல்": "ல",
    "எச்": "க",
    "ஆர்": "ர",
    "என்": "ந",
    "ஏ": "அ",
    "கே": "க",
    "பி": "ப",
    "டி": "த",
    "வி": "வ",
    "ஜி": "ச",
    "ஜே": "ச",
    "சி": "ச",
}
LATIN = dict(zip("ABCDGHJKLMNPRSTV", "அபசதசகசகலமநபரசதவ", strict=True))
CONSONANT_CLASS = str.maketrans(
    {"ண": "ந", "ன": "ந", "ள": "ல", "ழ": "ல", "ற": "ர", "ஷ": "ச", "ஸ": "ச",
     "ஜ": "ச", "ட": "த", "ஆ": "அ", "எ": "அ", "ஏ": "அ"}
)  # fmt: skip
KEYING = [
    ("ாி", "ரி"),
    ("ாீ", "ரீ"),
    ("ா்", "ர்"),
    ("ொி", "ெரி"),
    ("ோி", "ேரி"),
    ("ொீ", "ெரீ"),
    ("ோீ", "ேரீ"),
    ("ஶ", "ஸ"),
]
FOLDS = [
    (r"ீ", "ி"),
    (r"ூ", "ு"),
    (r"ே", "ெ"),
    (r"ோ", "ொ"),
    (r"[ணன]", "ந"),
    (r"[ளழ]", "ல"),
    (r"ற", "ர"),
    (r"[ஷஸஜ]", "ச"),
    (r"([ா-ௌ])[ா-ௌ]+", r"\1"),  # decoding residue: two vowel signs in a row
    (r"[ஙஞம]்(?=[க-ஹ])", "ந்"),  # nasal before a consonant, typed either way
    (r"([க-ஹ])்\1", r"\1"),  # doubled consonant at a join
]
VOWEL_SIGNS = re.compile(r"[ா-்ௗ]")
LENGTH_SIGNS = re.compile(r"[ா்]")
# word-start short forms of north and south: "வடகடப்பந்தாங்கல்", "தென்குச்சிபாளையம்"
SHORT_DIRECTIONS = [("வட", "N"), ("தென்", "S")]


def clean(name):
    text = unicodedata.normalize("NFC", name if isinstance(name, str) else "")
    for a, b in KEYING:
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def initial_class(token):
    if token in LATIN:
        return LATIN[token]
    if token in LETTER_NAMES:
        return LETTER_NAMES[token]
    return token[0].translate(CONSONANT_CLASS)


def qualifiers(name):
    """Qualifier families stated in a cleaned name, as {family: value}."""
    found = {}
    numbers = [m.group(1) for m in NUMBER.finditer(name)]
    if numbers:
        found["number"] = "+".join(
            str(ROMAN.get(n, int(n) if n.isdigit() else n)) for n in numbers
        )
    series = SERIES.search(name)
    if series:
        found["series"] = series.group(1)
    rest = SERIES.sub(" ", NUMBER.sub(" ", name))
    initials = [initial_class(m.group(1)) for m in INITIAL.finditer(rest)]
    trailing = TRAILING_INITIAL.search(rest)
    if trailing:
        initials.append(initial_class(trailing.group(1)))
    if initials:
        found["initials"] = "".join(initials)
    directions = {v for k, v in DIRECTIONS.items() if k in name}
    for word in re.split(r"[\s.()\-,]+", name):
        for prefix, value in SHORT_DIRECTIONS:
            if word.startswith(prefix) and not word.startswith("வடக்கு"):
                directions.add(value)
    for abbrev in re.findall(r"\(\s*([஀-௿]{1,2})\s*\)", name):
        if abbrev in DIRECTION_ABBREV:
            directions.add(DIRECTION_ABBREV[abbrev])
    if directions:
        found["direction"] = "".join(sorted(directions))
    words = [w for w in re.split(r"[\s.()\-,]+", name) if w]
    for family, prefixes in WORD_START.items():
        values = {v for w in words for p, v in prefixes if w.startswith(p)}
        if values:
            found[family] = "+".join(sorted(values))
    return found


def fold(name):
    """The name without its qualifiers, with spelling variation absorbed."""
    text = NUMBER.sub(" ", name)
    text = SERIES.sub(" ", text)
    text = TRAILING_INITIAL.sub(" ", text)
    text = INITIAL.sub(" ", text)
    text = re.sub(SECTION_WORDS, " ", text)
    text = re.sub(r"\(\s*[஀-௿]{1,2}\s*\)", " ", text)
    for word in DIRECTIONS:
        text = text.replace(word, " ")
    words = []
    for w in re.split(r"[\s.()\-,/]+", text):
        if re.match(r"இ[ரல]", w):
            w = w[1:]
        words.append(w)
    text = "".join(words)
    for pattern, replacement in FOLDS:
        text = re.sub(pattern, replacement, text)
    return re.sub(r"[^஀-௿]", "", text)


def skeleton(folded):
    """Consonants only: every vowel sign and the pulli stripped."""
    return VOWEL_SIGNS.sub("", folded)


def length_skeleton(folded):
    """The folded name without ா and the pulli: vowel length and a dropped
    pulli are ignored, vowel quality (i, u, e, o, ai) still counts."""
    return LENGTH_SIGNS.sub("", folded)


def similarity(a, b):
    """Largest of: the folded ratio; the length-skeleton ratio less 5 points;
    the full skeleton ratio less 12 points. 0-1.

    The full skeleton alone reaches at most 0.88, below the link threshold:
    it treats கோட்டமங்கலம் and குடிமங்கலம் as one name. It still matters, as a
    rival in the margin rule."""
    if not a or not b:
        return 0.0
    return (
        max(
            fuzz.ratio(a, b),
            fuzz.ratio(length_skeleton(a), length_skeleton(b)) - 5,
            fuzz.ratio(skeleton(a), skeleton(b)) - 12,
        )
        / 100
    )


def agree(qa, qb):
    return all(qa.get(k) == qb.get(k) for k in set(qa) | set(qb))


def truncated(a, b):
    """One folded name a short strict prefix of the other ("காசநாடு" against
    "காசநாடு புதூர்"): a part named after the whole, not the whole."""
    short, long = sorted((a, b), key=len)
    return short != long and long.startswith(short) and len(short) < 0.75 * len(long)
