"""Verify the published files, run the checks, and write MANIFEST.json.

Every check states what it appeals to. An `external` check compares the data
with a figure published elsewhere (or a second publication of the same
results) and can catch a misread; an `internal` check only shows the file
agrees with itself; a `legal` check compares with what the law requires. Each
records pass, warn or fail with the numbers behind it. `verify` exits non-zero
on a fail of a blocking check or on a hash mismatch.

Commands:
  verify   recompute hashes and checks, compare with data/MANIFEST.json
  write    rebuild data/MANIFEST.json
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata

import pandas as pd

from local_elections_tamil_nadu.parse.common import DATA, ROOT

MANIFEST = DATA / "MANIFEST.json"
README = ROOT / "README.md"
MARK = ("<!-- checks:start -->", "<!-- checks:end -->")
OUTPUTS = [
    "2011/vp_president_results.parquet",
    "2011/vp_president_candidates.parquet",
    "2019/vp_president_results.parquet",
    "2019/vp_president_candidates.parquet",
    "2019/app_winners.parquet",
    "2019/app_union_counts.parquet",
    "2021/vp_president_results.parquet",
    "2021/vp_president_candidates.parquet",
    "checks/hand_check.csv",
    "linkage/union_crosswalk_2011_2019_2021.csv",
    "linkage/review_2011_2019_2021.csv",
    "linkage/vp_2011_2019.parquet",
    "linkage/vp_2011_2021.parquet",
]
# The commission's 2011 state abstracts (data/raw/tnsec/rulbe2011/abstract_*.pdf),
# row "சிற்றூராட்சி தலைவர்" (village panchayat president), read 2026-10-18.
SEC_2011 = {
    "posts": 12524,
    "elected": 12523,
    "no_nomination": 1,
    "women_reserved": {"ST": 38, "SC": 1164, "NONE": 3089},
    # winners by sex: abstract_categorywise.pdf (table 7), summing its
    # ST/SC/general women and men columns
    "winners_by_sex": {"female": 73 + 1812 + 3099, "male": 117 + 2265 + 5157},
}
# 2021 ordinary election in nine districts: 2,901 president posts, 119 of them
# filled unopposed (SEC figures as reported by The News Minute, 2021-10-12).
SEC_2021 = {"posts": 2901, "unopposed": 119}
ORDINARY_2021 = {"kpm", "cpt", "vlr", "tpt", "rpt", "vpm", "kki", "tnv", "tki"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def result(name, appeals_to, status, detail, blocking=False, **numbers):
    return {
        "check": name,
        "appeals_to": appeals_to,
        "status": status,
        "blocking": blocking,
        "detail": detail,
        **numbers,
    }


def load(year, kind):
    return pd.read_parquet(DATA / str(year) / f"vp_president_{kind}.parquet")


def ordinary(df):
    return df[df["election_type"] == "General Election"]


def key(text):
    """Comparison key for a Tamil name: letters only, NFC."""
    text = unicodedata.normalize("NFC", str(text or ""))
    # Some names were keyed with ா for ர before ி/ீ ("மாாியம்மாள்"); that
    # sequence cannot occur in Tamil, so fold it for comparison only.
    text = text.replace("ாி", "ரி").replace("ாீ", "ரீ")
    return re.sub(r"[^஀-௿]", "", text)


# ------------------------------------------------------------------ internal


def internal(year):
    s, c = load(year, "results"), load(year, "candidates")
    out = []
    multi = s["quality_flags"].str.contains("elected_rows")
    out.append(
        result(
            f"{year}_one_winner_per_seat",
            "internal",
            "pass" if not multi.any() else "fail",
            "each seat has exactly one candidate marked won or elected unopposed",
            blocking=True,
            seats=len(s),
            flagged=int(multi.sum()),
        )
    )
    blank = s["quality_flags"].str.contains("reservation_blank_in_source")
    bad = (s["caste_reservation"].isna() | s["woman_reserved"].isna()) & ~blank
    out.append(
        result(
            f"{year}_reservation_read",
            "internal",
            "pass" if not bad.any() else "fail",
            "every seat's bracketed reservation maps to SC/ST/general x woman or "
            "not; brackets printed empty are left unknown and counted separately",
            blocking=True,
            unread=int(bad.sum()),
            blank_in_source=int(blank.sum()),
        )
    )
    sums = c.groupby(["election", "district_code", "block_seq"]).agg(
        votes=("votes", "sum"), valid=("valid_votes", "first"), n=("votes", "size")
    )
    contested = sums[sums["valid"].notna() & (sums["n"] > 1)]
    off = contested[contested["votes"] != contested["valid"]]
    out.append(
        result(
            f"{year}_votes_add_up",
            "internal",
            "pass"
            if len(off) == 0
            else ("warn" if len(off) < 0.01 * len(contested) else "fail"),
            "candidate votes sum to the printed valid votes (catches dropped rows)",
            contested=len(contested),
            mismatched=len(off),
        )
    )
    unknown = c["candidate_name"].str.contains("⟦", na=False) | c[
        "relation_name"
    ].str.contains("⟦", na=False)
    # a vowel sign after another sign or at the start of a word cannot occur in
    # Tamil; a period after a space means punctuation was misplaced
    # The commission keyed some ர as ா ("மாாியம்மாள்"), giving ாி/ொி etc.;
    # those are counted apart as source keying, not misordering.
    keyed = r"[ாொோ][ிீ]|ா்"
    odd = r"^\.|(?:^|\s)[ாிீுூ்]|[்ிீுூெேைௌ][ிீ]"
    source_keyed = sum(
        int(df[col].str.contains(keyed, na=False).sum())
        for df, col in [(c, "candidate_name"), (c, "relation_name")]
    )
    misordered = sum(
        int(df[col].str.contains(odd, na=False).sum())
        for df, col in [
            (c, "candidate_name"),
            (c, "relation_name"),
            (s, "gram_panchayat"),
            (s, "block"),
        ]
    )
    sex = c["candidate_gender"].isna()
    out.append(
        result(
            f"{year}_glyphs_and_sex_decoded",
            "internal",
            "pass"
            if not unknown.any() and not sex.any() and misordered < 20
            else "warn",
            "no undecoded glyph in names; every candidate's printed sex recognised; "
            "few names with a sequence Tamil cannot have (misordered glyphs)",
            undecoded=int(unknown.sum()),
            misordered_names=misordered,
            names_with_source_keying=source_keyed,
            sex_unread=int(sex.sum()),
        )
    )
    contested = s[~s["unopposed"] & s["votes"].notna() & s["runner_up_votes"].notna()]
    not_top = contested[contested["votes"] < contested["runner_up_votes"]]
    out.append(
        result(
            f"{year}_winner_has_most_votes",
            "internal",
            "pass" if len(not_top) == 0 else "warn",
            "the candidate marked won has at least the runner-up's votes",
            exceptions=len(not_top),
        )
    )
    return out


# ------------------------------------------------------------------ 2011


def checks_2011():
    s = load(2011, "results")
    out = []
    n = len(s)
    out.append(
        result(
            "2011_seats_vs_sec_abstract",
            "external",
            "pass" if n in (SEC_2011["elected"], SEC_2011["posts"]) else "fail",
            "seats parsed vs the commission's abstract: 12,524 posts, 12,523 filled",
            blocking=True,
            parsed=n,
            sec_posts=SEC_2011["posts"],
            sec_elected=SEC_2011["elected"],
        )
    )
    got = s[s["woman_reserved"] == True].groupby("caste_reservation").size()  # noqa: E712
    diffs = {k: int(got.get(k, 0)) - v for k, v in SEC_2011["women_reserved"].items()}
    blank = int(s["quality_flags"].str.contains("reservation_blank_in_source").sum())
    gap = sum(map(abs, diffs.values()))
    out.append(
        result(
            "2011_women_reserved_vs_sec_abstract",
            "external",
            "pass" if gap == 0 else ("warn" if gap <= blank else "fail"),
            "women-reserved seats by caste category vs abstract_women.pdf; seats "
            "whose bracket is printed empty cannot be counted and may explain a gap",
            blocking=True,
            parsed={k: int(got.get(k, 0)) for k in SEC_2011["women_reserved"]},
            sec=SEC_2011["women_reserved"],
            blank_in_source=blank,
        )
    )
    sex = s["winner_gender"].value_counts()
    cells = {g: (int(sex.get(g, 0)), v) for g, v in SEC_2011["winners_by_sex"].items()}
    gap = sum(abs(a - b) for a, b in cells.values())
    out.append(
        result(
            "2011_winners_by_sex_vs_sec_abstract",
            "external",
            "pass" if gap == 0 else ("warn" if gap <= 10 else "fail"),
            "winners by printed sex vs abstract_categorywise.pdf (whose categories "
            "are the winners' own caste, not the seat's: it counts 4,077 SC "
            "winners against 3,132 SC-reserved seats, so only the sex totals "
            "are comparable)",
            blocking=True,
            parsed_vs_sec=cells,
            total_abs_gap=gap,
        )
    )
    ref = pd.read_csv(DATA / "reference" / "gazette318_2011_counts.csv")
    names = pd.read_csv(DATA / "reference" / "districts.csv").dropna()
    fold = {
        "General": ("NONE", False),
        "General (Women)": ("NONE", True),
        "SC (General)": ("SC", False),
        "SC (Women)": ("SC", True),
        "ST (General)": ("ST", False),
        "ST (Women)": ("ST", True),
    }
    ref = ref[ref["reservation"].isin(fold)]
    ref[["caste_reservation", "woman_reserved"]] = ref["reservation"].map(fold).tolist()
    ref = ref.merge(names, left_on="district", right_on="gazette_2011_district")
    a = ref.groupby(["district_code", "caste_reservation", "woman_reserved"])[
        "gp_count"
    ].sum()
    b = s.groupby(["district_code", "caste_reservation", "woman_reserved"]).size()
    both = pd.concat([a.rename("gazette"), b.rename("results")], axis=1).fillna(0)
    diff = both[both["gazette"] != both["results"]]
    out.append(
        result(
            "2011_district_category_counts_vs_gazette_318",
            "external",
            "pass" if diff.empty else "warn",
            "seats per district x reservation in the results vs the September 2011 "
            "GO61 roster (Gazette 318, parsed independently in local_elections); "
            "differences can be real (later amendments, no-nomination seats)",
            cells=len(both),
            cells_differing=len(diff),
            seats_differing=int((diff["gazette"] - diff["results"]).abs().sum()),
            examples=[
                {"cell": "/".join(map(str, k)), **{c: int(v) for c, v in r.items()}}
                for k, r in diff.head(8).iterrows()
            ],
        )
    )
    share = s["woman_reserved"].mean()
    out.append(
        result(
            "2011_women_reserved_share",
            "legal",
            "pass" if 0.33 <= share < 0.4 else "warn",
            "2011 reserved one third of offices for women (50% came in 2016)",
            share=round(float(share), 4),
        )
    )
    return out


# ------------------------------------------------------------------ 2019


def checks_2019():
    s = load(2019, "results")
    app = pd.read_parquet(DATA / "2019" / "app_winners.parquet")
    unions = pd.read_parquet(DATA / "2019" / "app_union_counts.parquet")
    out = []
    posts = int(unions["posts_total"].sum())
    out.append(
        result(
            "2019_seats_vs_results_application",
            "external",
            "pass"
            if len(s) == posts
            else ("warn" if abs(len(s) - posts) <= 10 else "fail"),
            "seats in the PDFs (including headings printed with no candidate) vs "
            "posts in the commission's results application; the application's "
            "other rows are panchayats it marks 'result not declared'",
            blocking=True,
            parsed=len(s),
            parsed_no_candidates=int(s["vacant"].sum()),
            app_posts=posts,
            app_posts_no_nomination=int(unions["posts_no_nomination"].sum()),
            app_rows=len(app),
        )
    )
    s = s.assign(
        k_block=s["block"].map(place_key), k_gp=s["gram_panchayat"].map(place_key)
    )
    app = app.assign(
        k_block=app["block"].map(place_key),
        k_gp=app["gram_panchayat"].map(place_key),
    )
    m = s.merge(
        app, on=["k_block", "k_gp"], how="left", suffixes=("", "_app"), indicator=True
    )
    matched = m[m["_merge"] == "both"]
    name_ok = matched.apply(
        lambda r: _same_person(r["winner"], r["winner_app"]), axis=1
    )
    sex = matched.dropna(subset=["winner_gender", "winner_gender_from_honorific"])
    sex_ok = (sex["winner_gender"] == sex["winner_gender_from_honorific"]).mean()
    out.append(
        result(
            "2019_winner_vs_results_application",
            "external",
            "pass" if name_ok.mean() > 0.97 and sex_ok > 0.97 else "warn",
            "PDF winner vs the application's winner for the same union and panchayat "
            "(two separately typed publications); sex compares printed sex with the "
            "application's honorific (திரு/திருமதி)",
            seats=len(s),
            joined_on_names=len(matched),
            winner_name_agree=round(float(name_ok.mean()), 4),
            sex_compared=len(sex),
            sex_agree=round(float(sex_ok), 4),
        )
    )
    out += women_share(s, 2019)
    return out


def _same_person(a, b):
    """Same name ignoring initials, order, spacing and punctuation.

    The PDFs print "NAME.INITIAL", the application "INITIAL NAME"; the
    longest word of either must appear among the other's words.
    """
    if not a or not b or pd.isna(a) or pd.isna(b):
        return False
    ta = {key(t) for t in re.split(r"[\s.,]+", str(a)) if len(key(t)) > 2}
    tb = {key(t) for t in re.split(r"[\s.,]+", str(b)) if len(key(t)) > 2}
    if not ta or not tb:
        return key(a) == key(b)
    return max(ta, key=len) in tb or max(tb, key=len) in ta


def place_key(text):
    """Comparison key for a place name: keeps digits and Roman numerals,
    which tell apart panchayats such as "85 X" and "87 X"."""
    text = unicodedata.normalize("NFC", str(text or ""))
    return re.sub(r"[^\u0b80-\u0bff0-9A-Za-z]", "", text)


def women_share(s, year):
    by = s.groupby("district_code")["woman_reserved"].mean()
    low = by[by < 0.495]
    return [
        result(
            f"{year}_women_reserved_share",
            "legal",
            "pass" if low.empty else "warn",
            "at least half of president offices reserved for women (Tamil Nadu "
            "Panchayats (Amendment) Act, 2016, L.A. Bill 5 of 2016, s.57), "
            "statewide and per district",
            share=round(float(s["woman_reserved"].mean()), 4),
            districts_below_half={k: round(float(v), 3) for k, v in low.items()},
        )
    ]


# ------------------------------------------------------------------ 2021


def checks_2021():
    s = load(2021, "results")
    o = ordinary(s)
    out = [
        result(
            "2021_ordinary_seats_vs_sec",
            "external",
            "pass"
            if len(o) == SEC_2021["posts"]
            else ("warn" if abs(len(o) - SEC_2021["posts"]) <= 10 else "fail"),
            "seats in the nine districts' files vs the 2,901 posts announced",
            blocking=True,
            parsed=len(o),
            sec=SEC_2021["posts"],
            casual_seats=int((s["election_type"] == "By Election").sum()),
        ),
        result(
            "2021_unopposed_vs_sec",
            "external",
            "pass" if int(o["unopposed"].sum()) == SEC_2021["unopposed"] else "warn",
            "presidents elected unopposed in the nine districts vs 119 reported",
            parsed=int(o["unopposed"].sum()),
            sec=SEC_2021["unopposed"],
        ),
    ]
    out += women_share(o, 2021)
    return out


# ------------------------------------------------------------------ links

LINK_KEY = ["district_code", "block", "gram_panchayat"]


def checks_links():
    """The 2011 -> 2019/2021 links (data/linkage/)."""
    out = []
    summary = json.loads(
        (DATA / "linkage" / "MANIFEST.json").read_text(encoding="utf-8")
    )
    early = pd.read_parquet(DATA / "2011" / "vp_president_results.parquet")
    problems = {}
    for year in (2019, 2021):
        links = pd.read_parquet(DATA / "linkage" / f"vp_2011_{year}.parquet")
        later = pd.read_parquet(DATA / str(year) / "vp_president_results.parquet")
        later = later[later["election_type"] == "General Election"]
        for side, rows in (("2011", early), (str(year), later)):
            keys = links[[f"{k}_{side}" for k in LINK_KEY]].set_axis(LINK_KEY, axis=1)
            counts = rows.groupby(LINK_KEY).size()
            found = counts.reindex(pd.MultiIndex.from_frame(keys))
            problems[f"{year}:{side}"] = {
                "repeated_in_links": int(keys.duplicated().sum()),
                "not_one_row": int((found != 1).sum()),
            }
    bad = sum(v for p in problems.values() for v in p.values())
    out.append(
        result(
            "links_keys_resolve_one_to_one",
            "internal",
            "pass" if bad == 0 else "fail",
            "each link side's (district_code, block, gram_panchayat) names exactly "
            "one row of its results table (2021: ordinary election rows), and no "
            "seat is linked twice",
            blocking=True,
            **problems,
        )
    )
    cw = pd.read_csv(DATA / "linkage" / "union_crosswalk_2011_2019_2021.csv")
    used = cw[cw["decision"] != "uncertain"]
    later_all = pd.concat(
        pd.read_parquet(DATA / str(y) / "vp_president_results.parquet").query(
            "election_type == 'General Election'"
        )
        for y in (2019, 2021)
    )
    miss_e = set(zip(early["district_code"], early["block"], strict=True)) - set(
        zip(used["district_2011"], used["block_2011"], strict=True)
    )
    miss_l = set(
        zip(later_all["district_code"], later_all["block"], strict=True)
    ) - set(zip(used["district_later"], used["block_later"], strict=True))
    out.append(
        result(
            "links_union_crosswalk_covers_all_unions",
            "internal",
            "pass" if not miss_e and not miss_l else "warn",
            "every 2011 and later panchayat union appears in a usable crosswalk row",
            decisions=cw["decision"].value_counts().to_dict(),
            unions_2011_uncovered=sorted(map("/".join, miss_e)),
            unions_later_uncovered=sorted(map("/".join, miss_l)),
        )
    )
    prec = summary["precision"]
    low = {b: v["precision"] for b, v in prec["bands"].items() if v["precision"] < 0.98}
    out.append(
        result(
            "links_precision_hand_review",
            "external",
            "pass" if not low and prec["estimate_stratified"] >= 0.98 else "fail",
            "hand review (data/linkage/review_2011_2019_2021.csv; unsure counts as "
            "wrong): precision at least 98% in every stratum and overall. Fuzzy "
            "links were read in full, exact links by sample",
            blocking=True,
            bands={
                b: f"{v['correct']}/{v['reviewed']} of {v['links']}, "
                f"CI {v['ci95'][0]}-{v['ci95'][1]}"
                for b, v in prec["bands"].items()
            },
            estimate=prec["estimate_stratified"],
            lower_bound=prec["lower_bound_stratified"],
        )
    )
    ind = summary["independent_check"]
    ok = (
        min(ind["linked_exact"], ind["linked_fuzzy"])
        >= 10 * ind["random_same_union_group"]
    )
    out.append(
        result(
            "links_share_candidates_vs_random",
            "external",
            "pass" if ok else "warn",
            "linked pairs share a candidate name across the two elections far more "
            "often than random pairs in the same union group (code shares nothing "
            "with the name match); exact and fuzzy links each at least ten times "
            "the random rate",
            **{
                k: ind[k]
                for k in ("linked_exact", "linked_fuzzy", "random_same_union_group")
            },
        )
    )
    return out


def stored_sha256(path):
    """sha256 of a raw file as stored, or None if it is not in the repo.

    Files over GitHub's 100 MB limit are committed as byte-split parts
    (`split -b 90m -a 1 FILE FILE.part_`); the hash is taken on the parts
    concatenated in order, which restores the original bytes.
    """
    if path.exists():
        return sha256(path)
    parts = sorted(path.parent.glob(path.name + ".part_*"))
    if not parts:
        return None
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.read_bytes())
    return digest.hexdigest()


def raw_problems():
    """Every logged raw file must be in the repo with the logged sha256."""
    with (DATA / "raw" / "fetch_log.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    problems = []
    for row in rows:
        got = stored_sha256(ROOT / row["path"])
        if got != row["sha256"]:
            problems.append(
                row["path"] + (" (missing)" if got is None else " (changed)")
            )
    return len(rows), problems


def run_checks():
    out = []
    for year in (2011, 2019, 2021):
        out += internal(year)
    out += checks_2011() + checks_2019() + checks_2021()
    out += checks_links()
    return out


def manifest():
    return {
        "outputs": {p: sha256(DATA / p) for p in OUTPUTS if (DATA / p).exists()},
        "checks": run_checks(),
    }


def checks_table(checks):
    """Markdown table of the checks, written into README.md between MARK."""
    lines = ["| Check | Against | Result | Numbers |", "|---|---|---|---|"]
    for c in checks:
        nums = {
            k: v
            for k, v in c.items()
            if k not in ("check", "appeals_to", "status", "blocking", "detail")
        }
        text = json.dumps(nums, ensure_ascii=False, default=str)
        text = text.replace("|", "/")[:300]
        lines.append(
            f"| `{c['check']}`: {c['detail']} | {c['appeals_to']} | "
            f"**{c['status']}** | {text} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "write"])
    args = parser.parse_args()
    new = manifest()
    for c in new["checks"]:
        print(f"{c['status']:5} {c['check']}")
    if args.command == "write":
        MANIFEST.write_text(
            json.dumps(new, indent=1, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        text = README.read_text(encoding="utf-8")
        head, rest = text.split(MARK[0], 1)
        tail = rest.split(MARK[1], 1)[1]
        README.write_text(
            f"{head}{MARK[0]}\n{checks_table(new['checks'])}\n{MARK[1]}{tail}",
            encoding="utf-8",
        )
        return
    old = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = [p for p, h in old["outputs"].items() if new["outputs"].get(p) != h]
    fails = [
        c["check"] for c in new["checks"] if c["blocking"] and c["status"] == "fail"
    ]
    logged, raw_bad = raw_problems()
    print(
        f"raw files: {logged - len(raw_bad)} of {logged} match data/raw/fetch_log.csv"
    )
    if raw_bad:
        print("raw file missing or changed:", raw_bad[:20])
    if bad:
        print("hash mismatch:", bad)
    if fails:
        print("blocking failures:", fails)
    sys.exit(1 if bad or fails or raw_bad else 0)


if __name__ == "__main__":
    main()
