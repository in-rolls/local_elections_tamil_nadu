"""Evidence for the hand-coded union crosswalk (2011 to 2019 / 2021).

For every 2011 panchayat union and every later union in the same district or
in a district carved from it: how many 2011 panchayats have their best name
match (similarity >= MATCH, equal qualifiers) in that later union, and how
many of those are exact after folding. Union names are printed beside. Writes
data/linkage/union_evidence_2011_2019_2021.csv (one row per union pair with
any shared panchayat). The decisions are made by hand in
data/manual/union_crosswalk_2011_2019_2021.csv, which this script does not
write.

    python -m local_elections_tamil_nadu.linkage.union_evidence
"""

import pandas as pd

from local_elections_tamil_nadu.linkage.names import (
    agree,
    clean,
    fold,
    qualifiers,
    similarity,
)
from local_elections_tamil_nadu.parse.common import RELEASE

OUT = RELEASE / "linkage" / "union_evidence_2011_2019_2021.csv"
MATCH = 0.80
# 2011 district -> districts covering its area later. The four districts
# split after 2011 voted in 2021; every other district voted in 2019.
LATER = {
    "kpm": ["kpm", "cpt"],
    "vlr": ["vlr", "tpt", "rpt"],
    "vpm": ["vpm", "kki"],
    "tnv": ["tnv", "tki"],
}


def seats(year):
    s = pd.read_parquet(RELEASE / str(year) / "vp_president_results.parquet")
    s = s[s["election_type"] == "General Election"].copy()
    s["year"] = year
    c = s["gram_panchayat"].map(clean)
    s["q"] = c.map(qualifiers)
    s["f"] = c.map(fold)
    return s[["year", "district_code", "block", "gram_panchayat", "q", "f"]]


def main():
    early = seats(2011)
    later = pd.concat([seats(2019), seats(2021)])
    rows = []
    for district, g in early.groupby("district_code"):
        cands = later[later["district_code"].isin(LATER.get(district, [district]))]
        for r in g.itertuples():
            scored = [
                (similarity(r.f, c.f), c.f == r.f, c.district_code, c.block, c.year)
                for c in cands.itertuples()
                if agree(r.q, c.q)
            ]
            best = max(scored, default=(0, False, "", "", 0))
            rows.append(
                {
                    "district_2011": district,
                    "block_2011": r.block,
                    "district_later": best[2] if best[0] >= MATCH else "",
                    "block_later": best[3] if best[0] >= MATCH else "",
                    "later_year": best[4] if best[0] >= MATCH else 0,
                    "exact": best[1],
                }
            )
    gp = pd.DataFrame(rows)
    size_e = early.groupby(["district_code", "block"]).size()
    size_l = later.groupby(["district_code", "block"]).size()
    pairs = (
        gp[gp["block_later"] != ""]
        .groupby(
            [
                "district_2011",
                "block_2011",
                "district_later",
                "block_later",
                "later_year",
            ]
        )
        .agg(shared=("exact", "size"), shared_exact=("exact", "sum"))
        .reset_index()
    )
    pairs["gps_2011"] = [
        size_e[(d, b)]
        for d, b in zip(pairs["district_2011"], pairs["block_2011"], strict=True)
    ]
    pairs["gps_later"] = [
        size_l[(d, b)]
        for d, b in zip(pairs["district_later"], pairs["block_later"], strict=True)
    ]
    pairs["share_of_2011"] = (pairs["shared"] / pairs["gps_2011"]).round(3)
    pairs["share_of_later"] = (pairs["shared"] / pairs["gps_later"]).round(3)
    pairs["names_fold_equal"] = [
        fold(clean(a)) == fold(clean(b))
        for a, b in zip(pairs["block_2011"], pairs["block_later"], strict=True)
    ]
    unmatched = (
        gp[gp["block_later"] == ""].groupby(["district_2011", "block_2011"]).size()
    )
    pairs["gps_2011_unmatched"] = [
        int(unmatched.get((d, b), 0))
        for d, b in zip(pairs["district_2011"], pairs["block_2011"], strict=True)
    ]
    pairs.to_csv(OUT, index=False)
    print(len(pairs), "union pairs")


if __name__ == "__main__":
    main()
