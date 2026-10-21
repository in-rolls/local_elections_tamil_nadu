"""Parse the rural ward-member result sheets (2011, 2019, 2021).

Three offices, each a separate sheet collected by collect/tnsec.py:
  vpwm  village panchayat ward member (one sheet per union from 2019)
  puwm  panchayat union ward member
  dpwm  district panchayat ward member

2019 and 2021 print, per ward, a heading ("<body> : NAME வார்டு எண்: N
[reservation]"), a line of electors and votes, and a ruled table with one row
per candidate: serial, name, sex, father's or husband's name, (party, for
puwm and dpwm), votes, percent, result. A heading at the foot of a page
belongs to the first table of the next page.

2011 prints only the winners: one ruled table per sheet, a row per ward with
village panchayat (or union), ward number, member, sex, community, the ward's
reservation and how the member was elected, under caption rows naming the
union.

Text is recovered with parse/tamil_fonts.py, as for the president sheets.

Outputs (data/<year>/), with tier vp_ward / pu_ward / dp_ward:
  ward_candidates.parquet  one row per candidate (2019, 2021)
  ward_results.parquet     one row per ward

Run: python -m local_elections_tamil_nadu.parse.wards
"""

import logging
import re

import pandas as pd
import pdfplumber

from local_elections_tamil_nadu.parse.common import DATA, RAW, page_chars, rel
from local_elections_tamil_nadu.parse.results import (
    ELECTIONS,
    ORDINARY_2021,
    SEX,
    TABLE,
    TOTALS,
    WOMAN,
    WON,
    cell_text,
    headings,
    reservation,
)

log = logging.getLogger("parse")

OFFICES = {
    # sheet prefix: (tier, the state's office, heading body label)
    "vpwm": ("vp_ward", "கிராம ஊராட்சி வார்டு உறுப்பினர்", r"கிராம\s*ஊராட்சி"),
    "puwm": ("pu_ward", "ஊராட்சி ஒன்றிய வார்டு உறுப்பினர்", r"ஊராட்சி\s*ஒன்றியம்"),
    "dpwm": ("dp_ward", "மாவட்ட ஊராட்சி வார்டு உறுப்பினர்", r"மாவட்டம்"),
}
WARD = re.compile(r"வார்டு\s*எண்\s*:\s*(\d+)")
UNION = re.compile(r"ஊராட்சி\s*ஒன்றியம்\s*:\s*(.+?)\s*$")


def fold_reservation(raw):
    """The printed category with 'ஆதிதிராவிடர்' (printed without its space on
    310 wards in 2011) read as 'ஆதி திராவிடர்'."""
    return re.sub(r"ஆதிதிராவிடர்", "ஆதி திராவிடர்", raw or "")


def heading_parts(text, office):
    """(body name, ward number, bracketed reservation) from a ward heading."""
    label = OFFICES[office][2]
    hit = re.search(
        rf"{label}\s*:\s*(?P<body>.+?)\s*வார்டு\s*எண்\s*:\s*(?P<ward>\d+)\s*"
        r"\[(?P<res>[^\]]*)\]",
        text,
    )
    if not hit:
        return None, None, None
    return hit["body"].strip(), hit["ward"], re.sub(r"\s+", " ", hit["res"]).strip()


def parse_modern(path, office, family):
    """Ward blocks from a 2019 or 2021 sheet."""
    blocks, current, pending, union = [], None, [], None
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            chars = page_chars(page)
            tables = sorted(page.find_tables(TABLE), key=lambda t: t.bbox[1])
            lines = headings(chars, tables, family)
            for _, line in lines:
                if (
                    office == "vpwm"
                    and (u := UNION.search(line))
                    and "வார்டு" not in line
                ):
                    union = u.group(1).strip()
            for t_index, table in enumerate(tables, 1):
                above = [line for y, line in lines if y < table.bbox[1]]
                lines = [(y, line) for y, line in lines if y >= table.bbox[1]]
                text = " ".join(pending + above)
                pending = []
                if WARD.search(text):
                    body, ward, res = heading_parts(text, office)
                    current = {
                        "heading_raw": text,
                        "heading_page": page_number,
                        "body": body,
                        "union": union,
                        "ward_no": ward,
                        "reserved_raw": res,
                        "rows": [],
                    }
                    for key, pattern in TOTALS.items():
                        hit = re.search(pattern, text)
                        current[key] = int(hit.group(1)) if hit else None
                    blocks.append(current)
                for r_index, row in enumerate(table.rows, 1):
                    cells = [
                        cell_text(chars, c, family) if c else "" for c in row.cells
                    ]
                    if (
                        not cells
                        or not re.fullmatch(r"\d+", cells[0])
                        or current is None
                    ):
                        continue
                    current["rows"].append(
                        {
                            "cells": cells,
                            "page": page_number,
                            "table": t_index,
                            "row": r_index,
                        }
                    )
            pending = [line for y, line in lines if line]
    return blocks


def modern_rows(blocks, election, district, office, path, year):
    tier, tier_local, _ = OFFICES[office]
    out = []
    for b_index, b in enumerate(blocks, 1):
        caste, woman, label, caste_local = reservation(
            fold_reservation(b["reserved_raw"])
        )
        for row in b["rows"] or [None]:
            cells = (row["cells"] if row else []) + [""] * 8
            if office == "vpwm":
                serial, name, sex, relation, votes, pct, result = cells[:7]
                party = None
            else:
                serial, name, sex, relation, party, votes, pct, result = cells[:8]
            out.append(
                {
                    "state": "Tamil Nadu",
                    "year": year,
                    "election": election,
                    "election_type": "General Election"
                    if election != "rlbe2021" or district in ORDINARY_2021
                    else "By Election",
                    "district_code": district,
                    "block": b["union"]
                    if office == "vpwm"
                    else (b["body"] if office == "puwm" else None),
                    "gram_panchayat": b["body"] if office == "vpwm" else None,
                    "ward_no": b["ward_no"],
                    "ward_seq": b_index,
                    "tier": tier,
                    "tier_local": tier_local,
                    "reserved_raw": b["reserved_raw"],
                    "reserved_caste": caste,
                    "reserved_caste_local": caste_local,
                    "reserved_woman": woman,
                    "reserved_label": label,
                    "electors": b["electors"],
                    "valid_votes": b["valid_votes"],
                    "candidate_no": serial or None,
                    "candidate_name": name or None,
                    "relation_name": relation or None,
                    "candidate_woman_raw": sex or None,
                    "candidate_woman": WOMAN.get(SEX.get(sex)),
                    "party": party or None,
                    "votes": int(votes) if re.fullmatch(r"\d+", votes) else None,
                    "vote_pct": float(pct) if re.fullmatch(r"\d+\.\d+", pct) else None,
                    "result": result or None,
                    "elected": any(w in result.replace(" ", "") for w in WON),
                    "placeholder": row is None,
                    "source_path": rel(path),
                    "source_page": row["page"] if row else b["heading_page"],
                    "source_table": row["table"] if row else None,
                    "source_row": row["row"] if row else None,
                    "heading_raw": b["heading_raw"],
                }
            )
    return out


def parse_2011(path, office, district, family):
    """One row per ward from a 2011 winners table."""
    tier, tier_local, _ = OFFICES[office]
    out, union = [], None
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            chars = page_chars(page)
            for t_index, table in enumerate(page.find_tables(TABLE), 1):
                for r_index, row in enumerate(table.rows, 1):
                    cells = [
                        cell_text(chars, c, family) if c else "" for c in row.cells
                    ]
                    joined = " ".join(cells)
                    if (
                        u := re.search(r"ஊராட்சி\s*ஒன்றியம்\s*:\s*(\S.*?)\s*$", joined)
                    ) and not re.fullmatch(r"\d+", cells[0]):
                        union = u.group(1).strip()
                        continue
                    if not cells or not re.fullmatch(r"\d+", cells[0]):
                        continue
                    cells += [""] * 8
                    if office == "dpwm":
                        _, ward, name, sex, community, res, mode = cells[:7]
                        body = None
                    else:
                        _, body, ward, name, sex, community, res, mode = cells[:8]
                    caste, woman, label, caste_local = reservation(
                        fold_reservation(res)
                    )
                    out.append(
                        {
                            "state": "Tamil Nadu",
                            "year": 2011,
                            "election": "rulbe2011",
                            "election_type": "General Election",
                            "district_code": district,
                            "block": union
                            if office == "vpwm"
                            else (body if office == "puwm" else None),
                            "gram_panchayat": body if office == "vpwm" else None,
                            "ward_no": ward or None,
                            "tier": tier,
                            "tier_local": tier_local,
                            "reserved_raw": res or None,
                            "reserved_caste": caste,
                            "reserved_caste_local": caste_local,
                            "reserved_woman": woman,
                            "reserved_label": label,
                            "winner": name or None,
                            "winner_woman_raw": sex or None,
                            "winner_woman": WOMAN.get(SEX.get(sex)),
                            "winner_community_raw": community or None,
                            "unopposed": "போட்டியின்றி" in mode,
                            "election_mode_raw": mode or None,
                            "source_path": rel(path),
                            "source_page": page_number,
                            "source_table": t_index,
                            "source_row": r_index,
                        }
                    )
    return out


def seats_from_candidates(cand):
    rows = []
    for _, g in cand.groupby(["source_path", "ward_seq"], sort=False):
        g = g.sort_values("votes", ascending=False, na_position="last")
        first, won = g.iloc[0], g[g["elected"]]
        flags = []
        if g["placeholder"].all():
            flags.append("no_candidates_printed")
        elif len(won) != 1:
            flags.append(f"elected_rows_{len(won)}")
        if first["reserved_caste"] is None:
            flags.append("reservation_not_read")
        w = won.iloc[0] if len(won) == 1 else None
        keep = [
            "state",
            "year",
            "election",
            "election_type",
            "district_code",
            "block",
            "gram_panchayat",
            "ward_no",
            "tier",
            "tier_local",
            "reserved_caste",
            "reserved_caste_local",
            "reserved_woman",
            "reserved_label",
            "reserved_raw",
            "electors",
            "valid_votes",
        ]
        rows.append(
            {
                **{k: first[k] for k in keep},
                "seat_candidates": 0 if g["placeholder"].all() else len(g),
                "winner": w["candidate_name"] if w is not None else None,
                "winner_woman_raw": w["candidate_woman_raw"] if w is not None else None,
                "winner_woman": w["candidate_woman"] if w is not None else None,
                "party": w["party"] if w is not None else None,
                "votes": w["votes"] if w is not None else None,
                "unopposed": bool(
                    g["result"].fillna("").str.contains("போட்டியின்றி").any()
                ),
                "source_path": first["source_path"],
                "source_page": int(w["source_page"])
                if w is not None
                else int(first["source_page"]),
                "heading_raw": first["heading_raw"],
                "quality_flags": ";".join(flags),
            }
        )
    return pd.DataFrame(rows)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    for election, (year, family) in ELECTIONS.items():
        cand, seats = [], []
        for office in OFFICES:
            for path in sorted((RAW / "tnsec" / election).glob(f"{office}_*.pdf")):
                district = path.stem.split("_")[1]
                # 2011 prints only the winners for village wards; its union
                # and district sheets list every candidate, as 2019 does
                if year == 2011 and office == "vpwm":
                    seats += parse_2011(path, office, district, family)
                else:
                    blocks = parse_modern(path, office, family)
                    cand += modern_rows(blocks, election, district, office, path, year)
            log.info("%s %s done", election, office)
        out = DATA / str(year)
        seat = pd.DataFrame(seats)
        if cand:
            cand = pd.DataFrame(cand)
            seat = pd.concat([seat, seats_from_candidates(cand)], ignore_index=True)
            cand = cand[~cand["placeholder"]].drop(columns="placeholder")
            for c in ("reserved_woman", "candidate_woman"):
                cand[c] = cand[c].astype("Int8")
            cand["votes"] = cand["votes"].astype("Int32")
            cand.to_parquet(out / "ward_candidates.parquet", index=False)
        for c in ("reserved_woman", "winner_woman"):
            seat[c] = seat[c].astype("Int8")
        for c in ("votes", "electors", "valid_votes", "seat_candidates"):
            if c in seat:
                seat[c] = seat[c].astype("Int32")
        seat.to_parquet(out / "ward_results.parquet", index=False)
        log.info("%s: %d wards", election, len(seat))


if __name__ == "__main__":
    main()
