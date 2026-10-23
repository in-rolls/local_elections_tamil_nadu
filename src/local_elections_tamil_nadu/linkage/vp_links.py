"""Link 2011 village panchayat president seats to their 2019 or 2021 seats.

Use: among seats open (not woman-reserved) in 2019/2021, compare those that
were women's seats in 2011 with those that were not. A wrong link adds noise
and can bias that comparison; a missing link only costs sample, so a doubtful
pair is left unlinked.

Blocking. A pair is a candidate only inside a union group: the 2011 and
later unions joined by the hand-coded crosswalk
(data/manual/union_crosswalk_2011_2019_2021.csv, decisions other than
`uncertain`), closed into connected components so that a split (Cuddalore's
three unions that gave panchayats to the new ஸ்ரீமுஷ்ணம்) forms one group.
preclink's Crosswalk maps each year's union key to its group; a key outside
the crosswalk keeps its year prefix and can meet nothing.

Score. The name comparison (linkage/names.py) is the largest of the ratio of
the folded names, the ratio of their length skeletons (ா and pulli dropped)
less 5 points, and the ratio of their full skeletons (all vowel signs
dropped) less 12 points; and 0 when a qualifier disagrees or one name is a
short prefix of the other. Nothing else is scored.

block_seq has weight 0. It is not a printed serial (the sheets print no
panchayat number) but the order of a panchayat in its district file, and that
order is not stable: among exact-name links inside unions the crosswalk calls
`same`, only 11.7% keep their rank within the union and the median rank
correlation is 0.52 (measured 2026-10-19). As a tie-breaker it could only
reorder candidates within the margin, which the margin rule drops anyway.

Not used: reservation, the winner's sex, winner or candidate names (the
analysis variables; candidate names are kept for the independent check).

Excluded: names that fold to nothing, and a name (with its qualifiers)
repeated within one union group in one year, which nothing in the files tells
apart.

Decision. preclink keeps pairs scoring at least THRESHOLD - MARGIN, drops a
left record whose best and second-best candidates are within MARGIN (so a
rival just under the threshold still counts), and assigns one-to-one by the
Hungarian method. The same is run with the years swapped, and a link must be
found both ways (the margin filter only looks at the left side). Links
scoring below THRESHOLD are then dropped. THRESHOLD was chosen from the hand
review in data/manual/linkage_review_2011_2019_2021.csv.

    python -m local_elections_tamil_nadu.linkage.vp_links
"""

import hashlib
import json
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from preclink import Pipeline
from preclink.block.crosswalk import Crosswalk
from rapidfuzz import fuzz

from local_elections_tamil_nadu.linkage import names
from local_elections_tamil_nadu.linkage.candidate_check import check
from local_elections_tamil_nadu.linkage.union_evidence import LATER
from local_elections_tamil_nadu.parse.common import DATA, RELEASE

OUT = RELEASE / "linkage"
CROSSWALK = DATA / "manual" / "union_crosswalk_2011_2019_2021.csv"
REVIEW = DATA / "manual" / "linkage_review_2011_2019_2021.csv"
SOURCES = {
    y: RELEASE / str(y) / "vp_president_results.parquet" for y in (2011, 2019, 2021)
}
KEY = ["district_code", "block", "gram_panchayat"]
THRESHOLD = 0.94
MARGIN = 0.05


def components(crosswalk):
    """Union the crosswalk's union pairs into groups: node -> group name, and
    the decisions behind each group."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    usable = crosswalk[crosswalk["decision"] != "uncertain"]
    for r in usable.itertuples():
        a = f"2011|{r.district_2011}|{r.block_2011}"
        b = f"{r.later_year}|{r.district_later}|{r.block_later}"
        parent[find(a)] = find(b)
    roots = sorted({find(n) for n in list(parent)})
    label = {root: f"U{i:03d}" for i, root in enumerate(roots)}
    mapping = {n: label[find(n)] for n in list(parent)}
    kinds = {}
    for r in usable.itertuples():
        g = mapping[f"2011|{r.district_2011}|{r.block_2011}"]
        kinds.setdefault(g, set()).add(r.decision)
    return mapping, {g: "+".join(sorted(k)) for g, k in kinds.items()}


def seats(year, mapping):
    s = pd.read_parquet(SOURCES[year])
    s = s[s["election_type"] == "General Election"].reset_index(drop=True)
    s["year"] = year
    s["union_key"] = [
        f"{year}|{d}|{b}" for d, b in zip(s["district_code"], s["block"], strict=True)
    ]
    s["group"] = s["union_key"].map(mapping)
    cleaned = s["gram_panchayat"].map(names.clean)
    s["qualifiers"] = cleaned.map(names.qualifiers)
    s["name_folded"] = cleaned.map(names.fold)
    s["qkey"] = s["qualifiers"].map(
        lambda q: json.dumps(q, ensure_ascii=False, sort_keys=True)
    )
    return s


def usable(s):
    blank = s["name_folded"] == ""
    no_group = s["group"].isna()
    repeated = s.duplicated(["group", "name_folded", "qkey"], keep=False) & ~no_group
    excluded = {
        "no_crosswalked_union": int(no_group.sum()),
        "blank_name": int((blank & ~no_group).sum()),
        "name_repeated_in_group": int((repeated & ~blank).sum()),
    }
    u = s[~(blank | no_group | repeated)].copy()
    u["name_key"] = list(zip(u["name_folded"], u["qualifiers"], strict=True))
    return u.reset_index(drop=True), excluded


def score(a, b):
    (fa, qa), (fb, qb) = a, b
    if not names.agree(qa, qb) or names.truncated(fa, fb):
        return 0.0
    return names.similarity(fa, fb)


@dataclass(frozen=True, slots=True)
class PlaceName:
    """preclink comparison on (folded name, qualifiers)."""

    column: str = "name_key"
    weight: float = 1.0

    def compare(self, left, right):
        return pd.Series(
            [score(a, b) for a, b in zip(left, right, strict=True)], index=left.index
        )


def one_way(left, right, mapping, threshold):
    pipeline = (
        Pipeline()
        .block(on="union_key", crosswalk=Crosswalk(mapping))
        .score(comparisons=[PlaceName()])
        .filter(min_score=threshold - MARGIN, margin=MARGIN)
        .decide(method="hungarian")
        .build()
    )
    cols = ["union_key", "name_key"]
    return pipeline.link(left[cols], right[cols]).matches


def link(left, right, mapping, threshold=THRESHOLD):
    fwd = one_way(left, right, mapping, threshold)
    back = one_way(right, left, mapping, threshold)
    mutual = set(zip(back["right_index"], back["left_index"], strict=True))
    keep = [
        (li, ri) in mutual and s >= threshold
        for li, ri, s in zip(
            fwd["left_index"], fwd["right_index"], fwd["score"], strict=True
        )
    ]
    return fwd[keep].reset_index(drop=True)


def candidates(left, right, mapping, low, high):
    """Every same-group pair scoring in [low, high): for the near-miss review."""
    right = right.assign(g=right["union_key"].map(mapping))
    out = []
    for r in left.itertuples():
        g = mapping.get(r.union_key)
        for c in right[right["g"] == g].itertuples():
            sc = score(r.name_key, c.name_key)
            if low <= sc < high:
                out.append((r.Index, c.Index, sc))
    return pd.DataFrame(out, columns=["left_index", "right_index", "score"])


def band(row):
    """Review stratum of a link."""
    if row["link_rule"] == "exact_folded_name":
        same = row["gram_panchayat_2011"] == row["gram_panchayat_later"]
        return "exact" if same else "exact_respelled"
    return "0.97-1.00" if row["name_score"] >= 0.97 else "0.94-0.97"


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(float(centre - half), 4), round(float(centre + half), 4))


def precision(table):
    """Precision by stratum from the hand review, on reviewed pairs that are
    still links; `unsure` counts as incorrect. Fuzzy links were reviewed in
    full, exact ones by sample."""
    review = pd.read_csv(REVIEW)
    sample = review[review["kind"] == "link_sample"]
    keys = [f"{k}_{y}" for y in ("2011", "later") for k in KEY]
    final = table.assign(band=table.apply(band, axis=1))
    merged = sample.merge(
        final[[*keys, "band"]], on=keys, how="inner", suffixes=("_reviewed", "")
    )
    sizes = final["band"].value_counts()
    bands, lower = {}, 0.0
    for name in sizes.index:
        group = merged[merged["band"] == name]
        k, n = int((group["decision"] == "correct").sum()), len(group)
        low, high = wilson(k, n)
        bands[name] = {
            "links": int(sizes[name]),
            "reviewed": n,
            "correct": k,
            "precision": round(k / n, 4) if n else None,
            "ci95": [low, high],
        }
        lower += sizes[name] / sizes.sum() * (low or 0)
    estimate = sum(
        sizes[b] / sizes.sum() * v["precision"]
        for b, v in bands.items()
        if v["reviewed"]
    )
    near = review[review["kind"] != "link_sample"]
    by_near = {
        f"{kind}:{b}": {
            "pairs": len(g),
            "correct": int((g["decision"] == "correct").sum()),
            "unsure": int((g["decision"] == "unsure").sum()),
            "incorrect": int((g["decision"] == "incorrect").sum()),
        }
        for (kind, b), g in near.groupby(["kind", "band"])
    }
    return {
        "bands": bands,
        "reviewed_links": len(sample),
        "reviewed_still_linked": len(merged),
        "estimate_stratified": round(float(estimate), 4),
        "lower_bound_stratified": round(float(lower), 4),
        "below_threshold": by_near,
    }


def by_district(table, early, later):
    later_of = {code: [code] for code in early["district_code"].unique()}
    later_of.update(LATER)
    rows = []
    for district in sorted(early["district_code"].unique()):
        targets = later_of[district]
        rows.append(
            {
                "district_2011": district,
                "later_districts": "+".join(targets),
                "later_year": int(
                    later[later["district_code"].isin(targets)]["year"].iloc[0]
                ),
                "seats_2011": int((early["district_code"] == district).sum()),
                "seats_later": int(later["district_code"].isin(targets).sum()),
                "linked": int((table["district_code_2011"] == district).sum()),
            }
        )
    return rows


def side(frame, suffix):
    return {f"{k}_{suffix}": frame[k].to_numpy() for k in KEY} | {
        f"source_page_{suffix}": frame["source_page"].to_numpy(),
        f"name_folded_{suffix}": frame["name_folded"].to_numpy(),
    }


def build(threshold=THRESHOLD):
    crosswalk = pd.read_csv(CROSSWALK)
    mapping, kinds = components(crosswalk)
    early = seats(2011, mapping)
    later = pd.concat([seats(2019, mapping), seats(2021, mapping)], ignore_index=True)
    left, ex_left = usable(early)
    right, ex_right = usable(later)
    m = link(left, right, mapping, threshold)
    lt = left.loc[m["left_index"]].reset_index(drop=True)
    rt = right.loc[m["right_index"]].reset_index(drop=True)
    table = pd.DataFrame(
        {
            **side(lt, "2011"),
            "later_year": rt["year"].to_numpy(),
            **side(rt, "later"),
            "union_group": lt["group"].to_numpy(),
            "union_group_decisions": lt["group"].map(kinds).to_numpy(),
            "qualifiers": lt["qkey"].to_numpy(),
            "folded_ratio": [
                fuzz.ratio(a, b) / 100
                for a, b in zip(lt["name_folded"], rt["name_folded"], strict=True)
            ],
            "skeleton_ratio": [
                fuzz.ratio(names.skeleton(a), names.skeleton(b)) / 100
                for a, b in zip(lt["name_folded"], rt["name_folded"], strict=True)
            ],
            "name_score": m["score"].round(4).to_numpy(),
        }
    )
    table["link_rule"] = np.where(
        table["name_folded_2011"] == table["name_folded_later"],
        "exact_folded_name",
        "fuzzy_name",
    )
    return table, early, later, left, right, mapping, ex_left, ex_right


def by_year(table, year):
    t = table[table["later_year"] == year].drop(columns="later_year")
    t = t.rename(columns=lambda c: c.replace("_later", f"_{year}"))
    return t.sort_values([f"{k}_2011" for k in KEY]).reset_index(drop=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    table, early, later, _left, _right, _mapping, ex_l, ex_r = build()
    flags, independent = check(table)
    table["candidate_name_shared"] = flags
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for year in (2019, 2021):
        path = OUT / f"vp_2011_{year}.parquet"
        by_year(table, year).to_parquet(path, index=False)
        files[path.name] = {
            "rows": int((table["later_year"] == year).sum()),
            "sha256": sha(path),
        }
    summary = {
        "purpose": "2011 to 2019/2021 village panchayat president seat links, "
        "precision first. A link states that two panchayat names agree inside "
        "crosswalked unions, not that boundaries are unchanged.",
        "matcher": {
            "preclink": version("preclink"),
            "rapidfuzz": version("rapidfuzz"),
            "threshold": THRESHOLD,
            "margin": MARGIN,
            "mutual": True,
            "weights": {"name": 1.0, "block_seq": 0.0},
        },
        "links": {str(y): files[f"vp_2011_{y}.parquet"]["rows"] for y in (2019, 2021)},
        "exact_folded_name_links": int(
            (table["link_rule"] == "exact_folded_name").sum()
        ),
        "fuzzy_name_links": int((table["link_rule"] == "fuzzy_name").sum()),
        "excluded_2011": ex_l,
        "excluded_later": ex_r,
        "precision": precision(table),
        "independent_check": independent,
        "by_district": by_district(table, early, later),
        "inputs": {
            str(p.relative_to(DATA.parent)): sha(p)
            for p in [*SOURCES.values(), CROSSWALK, REVIEW]
        },
        "code_sha256": {
            m: sha(Path(__file__).with_name(m))
            for m in ("vp_links.py", "names.py", "candidate_check.py")
        },
        "outputs": files,
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k not in ("by_district", "inputs", "code_sha256")
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    return summary


if __name__ == "__main__":
    main()
