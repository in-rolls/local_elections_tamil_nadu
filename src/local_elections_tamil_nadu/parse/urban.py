"""Parse retained Chennai/Coimbatore urban records with source-specific fields."""

import csv
import gzip
import hashlib
import json
import re
from collections import Counter

import pandas as pd
import pdfplumber
import pyarrow as pa
import pyarrow.parquet as pq
from bs4 import BeautifulSoup

from local_elections_tamil_nadu.collect.fetch import ROOT, logged

RAW = ROOT / "data/raw/urban"
OUT = ROOT / "data/release/urban"
SOURCES = [
    "chennai_candidates_2011.html.gz",
    "chn_candidates_2022.csv",
    "cbe_candidates_2022.csv",
    "chn_wards_2022.csv",
    "cbe_wards_2022.csv",
    "chennai_reservation_2022.pdf",
    "coimbatore_councilors_2022.pdf",
]
CANDIDATE_SCHEMA = pa.schema(
    [
        pa.field("year", pa.int16(), nullable=False),
        pa.field("body", pa.string(), nullable=False),
        pa.field("ward_no", pa.string(), nullable=False),
        pa.field("candidate_no", pa.string(), nullable=False),
        pa.field("candidate_name", pa.string(), nullable=False),
        pa.field("party", pa.string(), nullable=False),
        pa.field("votes", pa.int32()),
        pa.field("result", pa.string(), nullable=False),
        pa.field("elected", pa.bool_(), nullable=False),
        pa.field("candidate_woman_raw", pa.string()),
        pa.field("candidate_woman", pa.int8()),
        pa.field("source_kind", pa.string(), nullable=False),
        pa.field("source_path", pa.string(), nullable=False),
        pa.field("source_row", pa.int32(), nullable=False),
        pa.field("source_sha256", pa.string(), nullable=False),
    ]
)
WINNER_RENAMES = {
    "candidate_name": "winner",
    "candidate_woman": "winner_woman",
    "candidate_woman_raw": "winner_woman_raw",
}
WINNER_SCHEMA = pa.schema(
    [
        *[
            pa.field(WINNER_RENAMES.get(f.name, f.name), f.type, nullable=f.nullable)
            for f in CANDIDATE_SCHEMA
        ],
        pa.field("winner_woman_basis", pa.string()),
        pa.field("reserved_raw_secondary", pa.string()),
        pa.field("reserved_raw", pa.string()),
        pa.field("reserved_caste", pa.string()),
        pa.field("reserved_woman", pa.int8()),
        pa.field("reserved_basis", pa.string()),
        pa.field("reserved_source_conflict", pa.bool_()),
        pa.field("councilor_name_raw", pa.string()),
        pa.field("councilor_party_raw", pa.string()),
        pa.field("councilor_source_page", pa.int16()),
        pa.field("councilor_link_basis", pa.string()),
        pa.field("is_geographic_link_validated", pa.bool_(), nullable=False),
    ]
)
RESERVED_SCHEMA = pa.schema(
    [
        pa.field("year", pa.int16(), nullable=False),
        pa.field("body", pa.string(), nullable=False),
        pa.field("ward_no", pa.string(), nullable=False),
        pa.field("reserved_caste", pa.string(), nullable=False),
        pa.field("reserved_woman", pa.int8()),
        pa.field("reserved_raw", pa.string()),
        pa.field("reserved_basis", pa.string(), nullable=False),
        pa.field("source_page", pa.int16(), nullable=False),
        pa.field("source_row", pa.int16()),
        pa.field("source_path", pa.string(), nullable=False),
        pa.field("source_sha256", pa.string(), nullable=False),
    ]
)
COUNCILOR_SCHEMA = pa.schema(
    [
        pa.field("year", pa.int16(), nullable=False),
        pa.field("body", pa.string(), nullable=False),
        pa.field("ward_no", pa.string(), nullable=False),
        pa.field("councilor_name_raw", pa.string(), nullable=False),
        pa.field("party", pa.string(), nullable=False),
        pa.field("source_page", pa.int16(), nullable=False),
        pa.field("source_path", pa.string(), nullable=False),
        pa.field("source_sha256", pa.string(), nullable=False),
    ]
)
CONFLICT_SCHEMA = pa.schema(
    [
        pa.field("year", pa.int16(), nullable=False),
        pa.field("body", pa.string(), nullable=False),
        pa.field("ward_no", pa.string(), nullable=False),
        pa.field("reserved_label_secondary", pa.string(), nullable=False),
        pa.field("reserved_caste", pa.string(), nullable=False),
        pa.field("reserved_woman", pa.int8()),
        pa.field("source_page", pa.int16(), nullable=False),
        pa.field("source_row", pa.int16(), nullable=False),
        pa.field("source_path", pa.string(), nullable=False),
        pa.field("source_sha256", pa.string(), nullable=False),
    ]
)
TABLES = {
    "reserved_source_conflicts": (
        CONFLICT_SCHEMA,
        ["year", "body", "ward_no"],
        2,
        "One secondary reservation label contradicted by the adopted "
        "primary notification",
    ),
    "candidates": (
        CANDIDATE_SCHEMA,
        ["year", "body", "ward_no", "candidate_no"],
        5920,
        "One candidate in one ward election",
    ),
    "winners": (
        WINNER_SCHEMA,
        ["year", "body", "ward_no"],
        500,
        "One published elected candidate in one ward election",
    ),
    "chennai_reservations_2022": (
        RESERVED_SCHEMA,
        ["year", "body", "ward_no"],
        200,
        "One ward under the January 17, 2022 notification",
    ),
    "coimbatore_councilors_2022": (
        COUNCILOR_SCHEMA,
        ["year", "body", "ward_no"],
        100,
        "One listed councilor in the March 2022 municipal PDF",
    ),
}
RELEASE_FILES = [
    *[f"{name}.parquet" for name in TABLES],
    "profile.json",
    "schema.json",
    "dictionary.csv",
    "checksums.json",
]


FIELD_NOTES = {
    "reserved_label_secondary": (
        "English reservation label in the secondary CSV, retained separately "
        "from the adopted primary notification."
    ),
    "year": "Election year labeled by the source; 2011 or 2022.",
    "body": "Municipal corporation: Chennai or Coimbatore, not the district.",
    "ward_no": (
        "Ward identifier stored as text; normalized numeric label, no "
        "historical geographic equivalence implied."
    ),
    "candidate_no": (
        "Printed candidate serial stored as text, unique within its ward election."
    ),
    "candidate_name": (
        "Candidate name as printed in the retained source; Tamil script "
        "retained; HTML whitespace normalized."
    ),
    "winner": (
        "Name of the candidate explicitly marked elected in the retained "
        "result source; not selected by maximum votes."
    ),
    "party": "Party label as printed, without cross-source grouping.",
    "votes": (
        "Printed integer vote count; null if unavailable, never substituted with zero."
    ),
    "result": "Printed election outcome label, retained in its source language.",
    "elected": (
        "Published Elected/WON status, including explicit lot/unopposed "
        "statuses; true for every winner row."
    ),
    "candidate_woman_raw": "Explicit source sex label; null in the 2011 republication.",
    "candidate_woman": (
        "1 for source Female, 0 for Male; null for Transgender or absent "
        "sex. No name or quota inference."
    ),
    "winner_woman_raw": (
        "Explicit sex label in the elected candidate's own source row; null in 2011."
    ),
    "winner_woman": (
        "1 for recorded Female, 0 for Male, null otherwise; never "
        "inferred from quota, names or photographs."
    ),
    "winner_woman_basis": (
        "published_candidate_row where sex is supplied; null when "
        "unavailable. Source kind records secondary origin."
    ),
    "source_kind": (
        "Result republication or secondary extraction from SEC PDFs; "
        "these are not certified primary result files."
    ),
    "source_path": (
        "Path to unchanged retained source bytes, relative to repository root."
    ),
    "source_row": (
        "HTML table row ordinal, PDF printed serial, or logical CSV "
        "record ordinal with header counted as 1; null for schedule "
        "complements."
    ),
    "source_sha256": "SHA-256 of retained bytes (compressed bytes for the 2011 HTML).",
    "source_page": (
        "1-based page of the original PDF; page 1 denotes the complete "
        "schedule frame for unlisted wards."
    ),
    "reserved_raw_secondary": (
        "Unchanged Tamil reservation text from the secondary ward "
        "extract, retained when contradicted by the primary gazette."
    ),
    "reserved_raw": (
        "Adopted source heading or reservation cell; null for an unlisted "
        "ward in the complete primary reserved schedule, or unavailable "
        "2011 data."
    ),
    "reserved_caste": (
        "Adopted seat caste quota: SC or NONE; NONE means unreserved by "
        "caste, not a statement about the winner; null if unknown."
    ),
    "reserved_woman": (
        "Adopted women quota: 1 reserved, 0 nonquota, null if unknown; "
        "distinct from candidate or winner sex."
    ),
    "reserved_basis": (
        "Which source or complete-roster complement supplied adopted "
        "quota values; null when unavailable."
    ),
    "reserved_source_conflict": (
        "True for a checked disagreement, false for checked agreement, "
        "null if not compared with a primary roster."
    ),
    "councilor_name_raw": (
        "English name in the official Coimbatore councilor PDF; retained "
        "as a separate measurement, not a verified identity match to the "
        "Tamil winner."
    ),
    "councilor_party_raw": (
        "Party in the official Coimbatore councilor PDF, separate from "
        "the candidate result source."
    ),
    "councilor_source_page": (
        "1-based page in coimbatore_councilors_2022.pdf; null for Chennai."
    ),
    "councilor_link_basis": (
        "Same 2022 body and ward; candidate identity is not independently "
        "validated by this join."
    ),
    "is_geographic_link_validated": (
        "False throughout; no cross-election ward link has been validated."
    ),
}
ENUMS = {
    "year": [2011, 2022],
    "body": ["Chennai", "Coimbatore"],
    "reserved_caste": ["SC", "NONE"],
    "candidate_woman": [0, 1],
    "winner_woman": [0, 1],
    "reserved_woman": [0, 1],
    "candidate_woman_raw": ["Male", "Female", "Transgender"],
    "winner_woman_raw": ["Male", "Female", "Transgender"],
}


def contracts():
    tables = {}
    for name, (schema, key, count, unit) in TABLES.items():
        fields = []
        for field in schema:
            kind = (
                "string"
                if pa.types.is_string(field.type)
                else ("boolean" if pa.types.is_boolean(field.type) else "integer")
            )
            constraints = {"required": not field.nullable}
            if field.name in ENUMS:
                constraints["enum"] = ENUMS[field.name]
            fields.append(
                {
                    "name": field.name,
                    "type": kind,
                    "arrow": str(field.type),
                    "nullable": field.nullable,
                    "constraints": constraints,
                    "description": FIELD_NOTES[field.name],
                }
            )
        tables[name] = {
            "path": f"{name}.parquet",
            "unit_of_observation": unit,
            "primaryKey": key,
            "expected_rows": count,
            "fields": fields,
        }
    return {
        "description": (
            "Source-specific urban supplement using pooled election "
            "vocabulary; incomplete pooled metadata is not fabricated."
        ),
        "tables": tables,
    }


def validate_table(name, table):
    schema, key, count, _ = TABLES[name]
    if not table.schema.equals(schema, check_metadata=False):
        raise ValueError(
            f"{name}: names, order, types or nullability differ from contract"
        )
    if table.num_rows != count:
        raise ValueError(f"{name}: row count differs from source frame")
    for field in schema:
        values = table[field.name]
        if not field.nullable and values.null_count:
            raise ValueError(f"{name}: required field {field.name} contains null")
        observed = {v for v in values.to_pylist() if v is not None}
        if field.name in ENUMS and not observed.issubset(ENUMS[field.name]):
            raise ValueError(f"{name}: invalid values in {field.name}")
    keys = [tuple(r[k] for k in key) for r in table.select(key).to_pylist()]
    if any(any(v is None or v == "" for v in k) for k in keys) or len(keys) != len(
        set(keys)
    ):
        raise ValueError(f"{name}: null or duplicate primary key")
    for subject in ("candidate", "winner"):
        if f"{subject}_woman" not in table.column_names:
            continue
        for raw, normalized in zip(
            table[f"{subject}_woman_raw"].to_pylist(),
            table[f"{subject}_woman"].to_pylist(),
            strict=True,
        ):
            if normalized != {"Female": 1, "Male": 0}.get(raw):
                raise ValueError(
                    f"{name}: recorded woman indicator disagrees with raw cell"
                )


def write_dictionary(out):
    with (out / "dictionary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "table",
                "column",
                "type",
                "nullable",
                "unit",
                "universe",
                "values",
                "missing",
                "n_missing",
                "description",
            ],
        )
        writer.writeheader()
        for name, (schema, _, _, unit) in TABLES.items():
            table = pq.read_table(out / f"{name}.parquet")
            for field in schema:
                writer.writerow(
                    {
                        "table": name,
                        "column": field.name,
                        "type": str(field.type),
                        "nullable": field.nullable,
                        "unit": unit,
                        "universe": name,
                        "values": json.dumps(ENUMS.get(field.name)),
                        "missing": (
                            "null: unavailable, not compared, or unsupported "
                            "classification; "
                            "see description"
                        ),
                        "n_missing": table[field.name].null_count,
                        "description": FIELD_NOTES[field.name],
                    }
                )


def validate_release(out=OUT):
    for name in TABLES:
        validate_table(name, pq.read_table(out / f"{name}.parquet"))
    if json.loads((out / "schema.json").read_text()) != contracts():
        raise ValueError("Published schema differs from declared table contracts")
    with (out / "dictionary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    expected = {
        (name, f.name) for name, (schema, _, _, _) in TABLES.items() for f in schema
    }
    actual = [(r["table"], r["column"]) for r in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Dictionary does not cover every table field exactly once")
    for row in rows:
        field = TABLES[row["table"]][0].field(row["column"])
        if (
            row["type"] != str(field.type)
            or row["description"] != FIELD_NOTES[field.name]
        ):
            raise ValueError("Dictionary differs from declared fields")
    checksums = json.loads((out / "checksums.json").read_text())
    expected_files = set(RELEASE_FILES) - {"checksums.json"}
    if set(checksums) != expected_files:
        raise ValueError("Urban checksum manifest has missing or unexpected files")
    for name, digest in checksums.items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Urban output checksum changed: {name}")
    return {name: pq.read_metadata(out / f"{name}.parquet").num_rows for name in TABLES}


def source_info(path):
    return {
        "source_path": str(path.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def verify_sources(raw=RAW):
    receipts = logged()
    for name in SOURCES:
        path = raw / name
        key = str(path.relative_to(ROOT))
        record = receipts[key]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record[
            "sha256"
        ] or path.stat().st_size != int(record["bytes"]):
            raise ValueError(f"Source changed: {key}")


def parse_2011(path):
    soup = BeautifulSoup(gzip.decompress(path.read_bytes()), "html.parser")
    heading = soup.find(string=lambda s: s and "Ward No:" in s)
    if heading is None or "Ward Members 2011" not in soup.get_text(" ", strip=True):
        raise ValueError("Not the dated Chennai 2011 result page")
    table = heading.find_parent("table")
    ward, rows = None, []
    info = source_info(path)
    for source_row, tr in enumerate(table.find_all("tr"), 1):
        cells = [
            c.get_text(" ", strip=True)
            for c in tr.find_all(["td", "th"], recursive=False)
        ]
        if len(cells) == 1 and (
            match := re.fullmatch(r"CHENNAI\s+Ward No:\s*(\d+)", cells[0])
        ):
            ward = str(int(match[1]))
        elif len(cells) == 5 and cells[0].isdigit():
            if ward is None or cells[4] not in {
                "Elected",
                "NotElected",
                "Deposit Lost",
            }:
                raise ValueError(f"Unexpected 2011 candidate: {cells}")
            rows.append(
                dict(
                    info,
                    year=2011,
                    body="Chennai",
                    ward_no=ward,
                    candidate_no=cells[0],
                    candidate_name=cells[1],
                    party=cells[2],
                    votes=int(cells[3]),
                    result=cells[4],
                    elected=cells[4] == "Elected",
                    candidate_woman_raw=None,
                    candidate_woman=None,
                    source_kind="livechennai_result_republication",
                    source_row=source_row,
                )
            )
    validate_frame(rows, 200)
    return rows


def validate_frame(rows, expected):
    keys = [(r["ward_no"], r["candidate_no"]) for r in rows]
    winners = [r["ward_no"] for r in rows if r["elected"]]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate candidate key")
    if len(winners) != expected or set(winners) != {
        str(n) for n in range(1, expected + 1)
    }:
        raise ValueError("Incomplete or duplicated winner frame")


def parse_2022(path, body, election_id, expected):
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame["source_row"] = range(2, len(frame) + 2)
    selected = frame.loc[frame.election_id.eq(election_id)]
    info, rows = source_info(path), []
    for r in selected.to_dict("records"):
        if r["gender"] not in {"Male", "Female", "Transgender"}:
            raise ValueError(f"Unknown source sex: {r['gender']}")
        if r["result"] not in {
            "WON",
            "LOST",
            "LOST_DEPOSIT_FORFEITED",
            "WON_BY_LOT",
            "UNOPPOSED_WON",
        }:
            raise ValueError(f"Unknown result: {r['result']}")
        rows.append(
            dict(
                info,
                year=2022,
                body=body,
                ward_no=r["ward_no"],
                candidate_no=r["serial"],
                candidate_name=r["name_ta"],
                party=r["party_ta"],
                votes=int(r["votes"]) if r["votes"] else None,
                result=r["result_ta"],
                elected=r["result"] in {"WON", "WON_BY_LOT", "UNOPPOSED_WON"},
                candidate_woman_raw=r["gender"],
                candidate_woman={"Male": 0, "Female": 1}.get(r["gender"]),
                source_kind="tamilnadudata_sec_pdf_extraction",
                source_row=r["source_row"],
            )
        )
    validate_frame(rows, expected)
    return rows


def chennai_reservations(path):
    output = {}
    with pdfplumber.open(path) as pdf:
        if "JANUARY 17, 2022" not in pdf.pages[0].extract_text():
            raise ValueError("Wrong reservation notification")
        for page in pdf.pages[1:]:
            headings = re.findall(
                r"Wards Reserved for "
                r"((?:Scheduled Castes|Women) \((?:General|Women)\))",
                page.extract_text(),
            )
            tables = page.extract_tables()
            if len(headings) != len(tables):
                raise ValueError("Reservation headings do not match tables")
            for number, table in enumerate(tables):
                category, woman = (
                    ("SC", int(number == 1)) if page.page_number == 2 else ("NONE", 1)
                )
                for r in table:
                    if len(r) == 2 and r[0] and r[0].isdigit():
                        ward = str(int(r[1]))
                        if ward in output:
                            raise ValueError("Duplicate reservation ward")
                        output[ward] = dict(
                            year=2022,
                            body="Chennai",
                            ward_no=ward,
                            reserved_raw=headings[number].strip(),
                            reserved_basis="printed_notification_schedule",
                            reserved_caste=category,
                            reserved_woman=woman,
                            source_page=page.page_number,
                            source_row=int(r[0]),
                            **source_info(path),
                        )
    if Counter((r["reserved_caste"], r["reserved_woman"]) for r in output.values()) != {
        ("SC", False): 16,
        ("SC", True): 16,
        ("NONE", True): 84,
    }:
        raise ValueError("Reservation totals differ from the printed schedule")
    for ward_number in range(1, 201):
        ward = str(ward_number)
        if ward not in output:
            output[ward] = dict(
                year=2022,
                body="Chennai",
                ward_no=ward,
                reserved_raw=None,
                reserved_basis="complement_of_complete_reserved_schedule",
                reserved_caste="NONE",
                reserved_woman=0,
                source_page=1,
                source_row=None,
                **source_info(path),
            )
    return output


def coimbatore_councilors(path):
    rows = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for r in table:
                    if len(r) != 8 or not r[0] or not r[0].isdigit():
                        continue
                    match = re.fullmatch(r"Ward-(\d+)", r[1])
                    if not match:
                        raise ValueError(f"Unexpected councilor ward: {r[1]}")
                    ward = str(int(match[1]))
                    if ward in rows:
                        raise ValueError("Duplicate official councilor ward")
                    rows[ward] = dict(
                        year=2022,
                        body="Coimbatore",
                        ward_no=ward,
                        councilor_name_raw=" ".join(r[2].split()),
                        party=" ".join(r[6].split()),
                        source_page=page.page_number,
                        **source_info(path),
                    )
    if set(rows) != {str(n) for n in range(1, 101)}:
        raise ValueError("Incomplete official Coimbatore roster")
    return rows


def secondary_reservation(value):
    caste = "SC" if value.startswith("Scheduled Caste") else "NONE"
    if value not in {
        "General",
        "General (Women)",
        "Scheduled Caste (General)",
        "Scheduled Caste (Women)",
    }:
        raise ValueError(f"Unknown secondary reservation: {value}")
    return caste, int("Women" in value)


def build(out=OUT):
    verify_sources()
    candidates = parse_2011(RAW / "chennai_candidates_2011.html.gz")
    for code, body, election_id, count in [
        ("chn", "Chennai", "TNULB-2022-CORP-CHENNAI", 200),
        ("cbe", "Coimbatore", "TNULB-2022-CORP-CBE-01", 100),
    ]:
        candidates.extend(
            parse_2022(RAW / f"{code}_candidates_2022.csv", body, election_id, count)
        )
    primary_reservations = chennai_reservations(RAW / "chennai_reservation_2022.pdf")
    primary_councilors = coimbatore_councilors(RAW / "coimbatore_councilors_2022.pdf")
    ward_tables = {}
    for code, body in [("chn", "Chennai"), ("cbe", "Coimbatore")]:
        path = RAW / f"{code}_wards_2022.csv"
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        selected = frame.loc[frame.election_id.str.contains("-CORP-")]
        if selected.ward_no.duplicated().any():
            raise ValueError("Duplicate secondary ward key")
        ward_tables[body] = {r["ward_no"]: r for r in selected.to_dict("records")}
    winners, conflicts = [], []
    for r in candidates:
        if not r["elected"]:
            continue
        w = dict(r, is_geographic_link_validated=False)
        if r["year"] == 2022:
            other = ward_tables[r["body"]][r["ward_no"]]
            if (r["candidate_name"], str(r["votes"]), r["party"]) != (
                other["winner_name_ta"],
                other["winner_votes"],
                other["winner_party_ta"],
            ):
                raise ValueError("Secondary candidate and ward winner disagree")
            caste, woman = secondary_reservation(other["reservation"])
            w.update(
                reserved_raw_secondary=other["reservation_ta"],
                reserved_raw=other["reservation_ta"],
                reserved_caste=caste,
                reserved_woman=woman,
                reserved_basis="secondary_ward_extract",
                reserved_source_conflict=None,
            )
            if r["body"] == "Chennai":
                primary = primary_reservations[r["ward_no"]]
                conflict = (caste, woman) != (
                    primary["reserved_caste"],
                    primary["reserved_woman"],
                )
                w.update(
                    reserved_raw=primary["reserved_raw"],
                    reserved_caste=primary["reserved_caste"],
                    reserved_woman=primary["reserved_woman"],
                    reserved_basis="official_january_17_2022_gazette",
                    reserved_source_conflict=conflict,
                )
                if conflict:
                    conflicts.append(
                        {
                            "ward_no": r["ward_no"],
                            "year": 2022,
                            "body": "Chennai",
                            "reserved_label_secondary": other["reservation"],
                            "reserved_caste": primary["reserved_caste"],
                            "reserved_woman": primary["reserved_woman"],
                            **{
                                key: primary[key]
                                for key in [
                                    "source_page",
                                    "source_row",
                                    "source_path",
                                    "source_sha256",
                                ]
                            },
                        }
                    )
            else:
                primary = primary_councilors[r["ward_no"]]
                w.update(
                    councilor_name_raw=primary["councilor_name_raw"],
                    councilor_party_raw=primary["party"],
                    councilor_source_page=primary["source_page"],
                    councilor_link_basis="same_2022_body_and_ward_not_identity_validated",
                )
        for old, new in WINNER_RENAMES.items():
            w[new] = w.pop(old)
        w["winner_woman_basis"] = (
            "published_candidate_row" if w["winner_woman_raw"] is not None else None
        )
        winners.append(w)
    out.mkdir(parents=True, exist_ok=True)
    tables = {
        "reserved_source_conflicts": conflicts,
        "candidates": candidates,
        "winners": winners,
        "chennai_reservations_2022": sorted(
            primary_reservations.values(), key=lambda r: int(r["ward_no"])
        ),
        "coimbatore_councilors_2022": sorted(
            primary_councilors.values(), key=lambda r: int(r["ward_no"])
        ),
    }
    for name, rows in tables.items():
        table = pa.Table.from_pylist(rows, schema=TABLES[name][0])
        validate_table(name, table)
        path = out / f"{name}.parquet"
        pq.write_table(table, path, compression="zstd")
        if not table.equals(pq.read_table(path)):
            raise ValueError("Parquet round trip changed data")
    profile = {
        "candidate_counts": dict(
            Counter(f"{r['body']} {r['year']}" for r in candidates)
        ),
        "winner_counts": dict(Counter(f"{r['body']} {r['year']}" for r in winners)),
        "winner_woman_raw_counts": dict(
            Counter(f"{r['body']} {r['year']} {r['winner_woman_raw']}" for r in winners)
        ),
        "reserved_source_conflicts": len(conflicts),
    }
    (out / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    (out / "schema.json").write_text(json.dumps(contracts(), indent=2) + "\n")
    write_dictionary(out)
    checksums = {
        name: hashlib.sha256((out / name).read_bytes()).hexdigest()
        for name in RELEASE_FILES
        if name != "checksums.json"
    }
    (out / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n")
    validate_release(out)

    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    build()
