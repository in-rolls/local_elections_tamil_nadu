"""Parse the village panchayat president result sheets (2011, 2019, 2021).

Reads only files saved by collect/tnsec.py. Each district PDF prints, per
village panchayat, a heading (union, panchayat, reservation in brackets), a
line of electors and votes, and a ruled table with one row per candidate:
serial, name, sex, father's or husband's name, votes, percent, result. A
table can run over a page break; a heading with no table after it on its page
belongs to the first table of the next page.

Cells are read from the table rulings, and text is recovered with
parse/tamil_fonts.py. Every candidate row keeps its page and table position.

Outputs (data/<year>/):
  vp_president_candidates.parquet  one row per candidate (candidates.json names)
  vp_president_results.parquet     one row per seat, collapsed from candidates
                                   (master.json names, plus winner_woman)

Run: python -m local_elections_tamil_nadu.parse.results
"""

import logging
import re
from collections import Counter

import pandas as pd
import pdfplumber
from pdfplumber.utils import cluster_objects

from local_elections_tamil_nadu.parse.common import (
    RAW,
    RELEASE,
    inside,
    page_chars,
    rel,
    text_lines,
)

log = logging.getLogger("parse")

ELECTIONS = {
    # election folder: (year, glyph family, print date of the poll)
    "rulbe2011": (2011, "latha"),
    "rlbe2019": (2019, "mpdf"),
    "rlbe2021": (2021, "mpdf"),
}
# Nine districts held their ordinary election in 2021; the rest of the 2021
# files are casual (by-) elections.
ORDINARY_2021 = {"kpm", "cpt", "vlr", "tpt", "rpt", "vpm", "kki", "tnv", "tki"}
TABLE = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
# A heading starts with either label; the parts can wrap onto up to three
# lines, and a long panchayat name pushes the bracket onto a line centred
# against the union label, so its words interleave, e.g.
# "கிராம ஊராட்சி : GP [ஆதி ஊராட்சி ஒன்றியம் : UNION திராவிடர் (பெண்கள்)]".
START = re.compile(r"(?:சிற்றூராட்சி|கிராம\s*ஊராட்சி)\s*:")
RES_WORDS = {
    "ஆதி",
    "திராவிடர்",
    "பழங்குடியினர்",
    "பொது",
    "(பெண்கள்)",
    "(பொது)",
    "(பெண்கள்",
    "(பொது",
    "பெண்கள்)",
    "பொது)",
    "(",
    ")",
}
TOTALS = {
    "electors": r"மொத்த\s*வாக்காளர்கள்\s*:\s*(\d+)",
    "votes_polled": r"பதிவான\s*வாக்குகள்\s*:\s*(\d+)",
    "valid_votes": r"செல்லத்தக்க\s*வாக்குகள்\s*:\s*(\d+)",
    "rejected_votes": r"செல்லாத\s*வாக்குகள்\s*:\s*(\d+)",
}
# female 1, male 0; "other" and anything unread stay blank rather than 0
WOMAN = {"female": 1, "male": 0}
SEX = {
    "ஆண்": "male",
    "பெண்": "female",
    "மற்றவர்": "other",
    "மூன்றாம் பாலினம்": "other",
    "திருநங்கை": "other",
}
CASTE = {"பொது": "NONE", "ஆதி திராவிடர்": "SC", "பழங்குடியினர்": "ST"}
# "வெற்றி" won; "போட்டியின்றி தேர்வு" elected unopposed.
WON = ("வெற்றி", "போட்டியின்றி")


def reservation(raw):
    """Fold the printed category; anything unrecognised stays unknown."""
    text = re.sub(r"\s+", " ", raw).strip(" []")
    woman = "பெண்கள்" in text
    caste_word = text.split("(", 1)[0].strip()
    caste = CASTE.get(caste_word)
    if caste is None:
        return None, None, None, caste_word or None
    label = {"NONE": "", "SC": "SC ", "ST": "ST "}[caste]
    label += "Woman" if woman else "Other than Woman"
    return caste, woman, label, caste_word


def split_heading(text):
    """Union, panchayat and bracketed reservation from a heading's text."""
    text = re.sub(r"மொத்த\s*வாக்காளர்கள்.*", "", text)
    text = re.sub(r"\s*([\[\]:])\s*", r" \1 ", text)
    tokens = text.split()
    parts = {"union": [], "gp": [], "res": []}
    mode, seen_bracket, i = None, False, 0
    while i < len(tokens):
        t = tokens[i]
        two = " ".join(tokens[i : i + 3])
        if two in ("ஊராட்சி ஒன்றியம் :", "கிராம ஊராட்சி :"):
            mode = "union" if "ஒன்றியம்" in two else "gp"
            i += 3
            continue
        if t == "சிற்றூராட்சி" and i + 1 < len(tokens) and tokens[i + 1] == ":":
            mode, i = "gp", i + 2
            continue
        if t == "[":
            mode, seen_bracket = "res", True
        elif t == "]":
            mode = None
        elif seen_bracket and t in RES_WORDS:
            parts["res"].append(t)
        elif mode:
            parts[mode].append(t)
        i += 1
    joined = {k: " ".join(v) or None for k, v in parts.items()}
    if joined["res"]:
        joined["res"] = re.sub(r"\(\s+|\s+\)", lambda m: m[0].strip(), joined["res"])
    return joined["union"], joined["gp"], joined["res"]


def cell_text(chars, bbox, family):
    glyphs = [dict(c) for c in inside(chars, bbox)]
    # 2011 prints "NAME.I." with the periods on a lower baseline; put each
    # punctuation mark on the line of the nearest letter so it stays in place.
    letters = [c for c in glyphs if c["text"] not in ".,"]
    for c in glyphs:
        if c["text"] in ".," and letters:
            mid = (c["top"] + c["bottom"]) / 2
            same_row = [
                o for o in letters if abs((o["top"] + o["bottom"]) / 2 - mid) < 10
            ]
            left = [o for o in same_row if o["x1"] <= c["x0"] + 1]
            near = (
                min(left, key=lambda o: c["x0"] - o["x1"])
                if left
                else min(letters, key=lambda o: abs((o["top"] + o["bottom"]) / 2 - mid))
            )
            c["top"], c["bottom"] = near["top"], near["bottom"]
    return re.sub(r"\s+", " ", " ".join(text_lines(glyphs, family))).strip()


def headings(chars, tables, family):
    """Text outside the tables, as (y, line) in reading order."""
    outside = [
        c
        for c in chars
        if not any(
            t.bbox[1] - 1 <= (c["top"] + c["bottom"]) / 2 <= t.bbox[3] + 1
            and t.bbox[0] - 1 <= (c["x0"] + c["x1"]) / 2 <= t.bbox[2] + 1
            for t in tables
        )
    ]
    out = []
    for group in cluster_objects(outside, "top", 3):
        for line in text_lines(group, family):
            out.append((min(c["top"] for c in group), line))
    return sorted(out)


def parse_pdf(path, election, district_code):
    year, family = ELECTIONS[election]
    blocks = []  # one per village panchayat
    current = None
    pending_heading = []  # heading lines waiting for their table

    def start_block(lines, page):
        text = " ".join(lines)
        union, gp, res = split_heading(text)
        block = {
            "heading_raw": text,
            "heading_page": page,
            "union_raw": union,
            "gp_raw": gp,
            "reserved_raw": res,
            "rows": [],
        }
        for key, pattern in TOTALS.items():
            hit = re.search(pattern, text)
            block[key] = int(hit.group(1)) if hit else None
        blocks.append(block)
        return block

    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            chars = page_chars(page)
            tables = sorted(page.find_tables(TABLE), key=lambda t: t.bbox[1])
            lines = headings(chars, tables, family)
            for t_index, table in enumerate(tables, 1):
                above = [line for y, line in lines if y < table.bbox[1]]
                lines = [(y, line) for y, line in lines if y >= table.bbox[1]]
                block_lines = pending_heading + above
                # the heading's page: the previous one when the label was
                # printed at its foot and nothing labelled this page's table
                head_page = (
                    page_number - 1
                    if START.search(" ".join(pending_heading))
                    and not START.search(" ".join(above))
                    else page_number
                )
                pending_heading = []
                if START.search(" ".join(block_lines)) or (
                    block_lines and current is None
                ):
                    current = start_block(block_lines, head_page)
                for r_index, row in enumerate(table.rows, 1):
                    cells = [
                        cell_text(chars, c, family) if c else "" for c in row.cells
                    ]
                    if not cells or not re.fullmatch(r"\d+", cells[0]):
                        continue  # column header
                    if len(cells) == 6:
                        # some 2011 files draw no rule at the table's right
                        # edge, so the result column is not detected
                        _, top, x1, bottom = row.bbox
                        cells.append(
                            cell_text(chars, (x1, top, page.width, bottom), family)
                        )
                    current["rows"].append(
                        {
                            "cells": cells,
                            "page": page_number,
                            "table": t_index,
                            "row": r_index,
                            "bbox": [round(v, 1) for v in row.bbox],
                            "table_top": round(table.bbox[1], 1),
                        }
                    )
            # heading printed at the foot of a page, table on the next
            pending_heading = [line for y, line in lines if line]
    return blocks, year, family


def candidate_rows(blocks, election, district_code, path, year):
    out = []
    for b_index, block in enumerate(blocks, 1):
        caste, woman, label, caste_local = reservation(block["reserved_raw"] or "")
        # a heading printed with no candidate table (no nomination) still
        # stands for a seat; it is carried as a placeholder row
        empty = {
            "cells": [""] * 7,
            "page": block["heading_page"],
            "table": None,
            "row": None,
            "bbox": None,
            "table_top": None,
            "placeholder": True,
        }
        for row in block["rows"] or [empty]:
            cells = row["cells"] + [""] * 7
            serial, name, sex, relation, votes, pct, result = cells[:7]
            out.append(
                {
                    "state": "Tamil Nadu",
                    "year": year,
                    "election": election,
                    "election_type": (
                        "General Election"
                        if election != "rlbe2021" or district_code in ORDINARY_2021
                        else "By Election"
                    ),
                    "district_code": district_code,
                    "block": block["union_raw"],
                    "gram_panchayat": block["gp_raw"],
                    "block_seq": b_index,
                    "tier": "gp_head",
                    "tier_local": "கிராம ஊராட்சித் தலைவர்",
                    "reserved_raw": block["reserved_raw"],
                    "reserved_caste": caste,
                    "reserved_caste_local": caste_local,
                    "reserved_woman": woman,
                    "reserved_label": label,
                    "electors": block["electors"],
                    "votes_polled": block["votes_polled"],
                    "valid_votes": block["valid_votes"],
                    "rejected_votes": block["rejected_votes"],
                    "candidate_no": serial,
                    "candidate_name": name,
                    "relation_name": relation,
                    "candidate_woman_raw": sex,
                    "candidate_woman": WOMAN.get(SEX.get(sex)),
                    "votes": int(votes) if re.fullmatch(r"\d+", votes) else None,
                    "vote_pct": float(pct) if re.fullmatch(r"\d+\.\d+", pct) else None,
                    "result": result,
                    "elected": any(w in result.replace(" ", "") for w in WON),
                    "source_path": rel(path),
                    "source_page": row["page"],
                    "source_table": row["table"],
                    "source_row": row["row"],
                    "source_bbox": row["bbox"],
                    "table_top": row["table_top"],
                    "heading_page": block["heading_page"],
                    "heading_raw": block["heading_raw"],
                    "placeholder": row.get("placeholder", False),
                }
            )
    return out


def seats(cand):
    rows = []
    keys = ["election", "district_code", "block_seq"]
    for _, g in cand.groupby(keys, sort=False):
        g = g.sort_values("votes", ascending=False, na_position="last")
        first = g.iloc[0]
        won = g[g["elected"]]
        flags = []
        none_printed = bool(g["placeholder"].all())
        if none_printed:
            flags.append("no_candidates_printed")
        elif len(won) != 1:
            flags.append(f"elected_rows_{len(won)}")
        if pd.isna(first["reserved_raw"]) and "[" in str(first["heading_raw"]):
            flags.append("reservation_blank_in_source")
        w = won.iloc[0] if len(won) else None
        others = g[~g["elected"]]
        ru = others.iloc[0] if len(others) and not g["placeholder"].all() else None
        unopposed = bool(g["result"].str.contains("போட்டியின்றி").any())
        rows.append(
            {
                **{
                    k: first[k]
                    for k in [
                        "state",
                        "year",
                        "election",
                        "election_type",
                        "district_code",
                        "block",
                        "gram_panchayat",
                        "block_seq",
                        "tier",
                        "tier_local",
                        "reserved_caste",
                        "reserved_caste_local",
                        "reserved_woman",
                        "reserved_label",
                        "reserved_raw",
                        "electors",
                        "votes_polled",
                        "valid_votes",
                        "rejected_votes",
                    ]
                },
                "listing_scope": "all_seats",
                "unit_of_observation": "seat_from_candidates",
                "seat_candidates": 0 if none_printed else len(g),
                "winner": w["candidate_name"] if w is not None else None,
                "winner_relation_name": w["relation_name"] if w is not None else None,
                "winner_woman_raw": w["candidate_woman_raw"] if w is not None else None,
                "winner_woman": w["candidate_woman"] if w is not None else None,
                # "வெற்றி (குலுக்கல் முறை)": won by drawing lots after a tie
                "winner_basis": (
                    "lot"
                    if w is not None and "குலுக்கல்" in w["result"]
                    else "uncontested"
                    if unopposed
                    else "published"
                ),
                "votes": w["votes"] if w is not None else None,
                "runner_up": ru["candidate_name"] if ru is not None else None,
                "runner_up_votes": ru["votes"] if ru is not None else None,
                "margin": (w["votes"] - ru["votes"])
                if w is not None
                and ru is not None
                and pd.notna(w["votes"])
                and pd.notna(ru["votes"])
                else None,
                "vacant": w is None,
                "unopposed": unopposed,
                "script": "tamil",
                "source_path": first["source_path"],
                "source_page": int(w["source_page"])
                if w is not None
                else int(first["source_page"]),
                "heading_page": first["heading_page"],
                "heading_raw": first["heading_raw"],
                "quality_flags": ";".join(flags),
            }
        )
    return pd.DataFrame(rows)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    for election, (year, _family) in ELECTIONS.items():
        cand = []
        for path in sorted((RAW / "tnsec" / election).glob("vpp_*.pdf")):
            code = path.stem.split("_", 1)[1]
            blocks, _, _ = parse_pdf(path, election, code)
            rows = candidate_rows(blocks, election, code, path, year)
            log.info(
                "%s %s: %d panchayats, %d candidates",
                election,
                code,
                len(blocks),
                len(rows),
            )
            cand += rows
        cand = pd.DataFrame(cand)
        out = RELEASE / str(year)
        out.mkdir(parents=True, exist_ok=True)
        seat = seats(cand)
        cand = cand[~cand["placeholder"]].drop(columns="placeholder")
        # 1 / 0 / null integers, as NAMING.md types every *_woman column
        for frame, columns in (
            (cand, ["reserved_woman", "candidate_woman"]),
            (seat, ["reserved_woman", "winner_woman"]),
        ):
            for column in columns:
                frame[column] = frame[column].astype("Int8")
        cand.to_parquet(out / "vp_president_candidates.parquet", index=False)
        seat.to_parquet(out / "vp_president_results.parquet", index=False)
        log.info(
            "%s: %d seats; flags %s",
            election,
            len(seat),
            Counter(seat["quality_flags"]).most_common(5),
        )


if __name__ == "__main__":
    main()
