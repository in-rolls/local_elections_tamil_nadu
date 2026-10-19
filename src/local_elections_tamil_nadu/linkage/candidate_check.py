"""Independent check on the links: shared candidate names.

Shares no code with the place-name match (linkage/names.py is not imported).
For a linked pair, does any candidate for president in 2011 have the same name
as any candidate for the same seat in 2019/2021? A re-contesting incumbent, a
runner-up or a family member with the same initial produces a shared name.
Correct links should share names far more often than random pairs drawn from
the same union group; if fuzzy links share names as often as exact ones,
fuzzy links are about as correct as exact ones.

A candidate name is compared after NFC, the commission's ா-for-ர keying
undone, every character outside the Tamil block dropped (so initials typed
in Latin are lost), and vowel length ignored.
"""

import re
import unicodedata

import numpy as np
import pandas as pd

from local_elections_tamil_nadu.parse.common import DATA

KEY = ["district_code", "block", "gram_panchayat"]
PERMUTATIONS = 50
SEED = 20261019


def person(name):
    text = unicodedata.normalize("NFC", name if isinstance(name, str) else "")
    text = text.replace("ாி", "ரி").replace("ாீ", "ரீ").replace("ா்", "ர்")
    text = re.sub(r"[^஀-௿]", "", text)
    for long, short in (("ீ", "ி"), ("ூ", "ு"), ("ே", "ெ"), ("ோ", "ொ")):
        text = text.replace(long, short)
    return text


def name_sets(year):
    c = pd.read_parquet(DATA / str(year) / "vp_president_candidates.parquet")
    if "election_type" in c:
        c = c[c["election_type"] == "General Election"]
    c = c.assign(p=c["candidate_name"].map(person))
    c = c[c["p"].str.len() >= 3]
    return c.groupby(KEY)["p"].agg(frozenset)


def shared(left_sets, right_sets):
    return np.array(
        [
            bool(a & b)
            if isinstance(a, frozenset) and isinstance(b, frozenset)
            else False
            for a, b in zip(left_sets, right_sets, strict=True)
        ]
    )


def check(links):
    """links: one row per link with KEY_2011, KEY_later, later_year,
    union_group, link_rule. Returns per-link flags and a summary."""
    s2011 = name_sets(2011)
    later = {y: name_sets(y) for y in (2019, 2021)}
    a = [s2011.get(tuple(k)) for k in links[[f"{c}_2011" for c in KEY]].to_numpy()]
    b = [
        later[y].get(tuple(k))
        for y, k in zip(
            links["later_year"],
            links[[f"{c}_later" for c in KEY]].to_numpy(),
            strict=True,
        )
    ]
    flags = shared(a, b)
    rng = np.random.default_rng(SEED)
    groups = links["union_group"].to_numpy()
    b_arr = np.empty(len(b), dtype=object)
    b_arr[:] = b
    random_rates = []
    for _ in range(PERMUTATIONS):
        perm = np.arange(len(b))
        for g in np.unique(groups):
            idx = np.flatnonzero(groups == g)
            perm[idx] = rng.permutation(idx)
        moved = perm != np.arange(len(b))
        flags_r = shared(a, list(b_arr[perm]))
        random_rates.append(flags_r[moved].mean())
    exact = (links["link_rule"] == "exact_folded_name").to_numpy()
    return flags, {
        "linked_all": round(float(flags.mean()), 4),
        "linked_exact": round(float(flags[exact].mean()), 4),
        "linked_fuzzy": round(float(flags[~exact].mean()), 4),
        "n_exact": int(exact.sum()),
        "n_fuzzy": int((~exact).sum()),
        "random_same_union_group": round(float(np.mean(random_rates)), 4),
        "random_permutations": PERMUTATIONS,
    }
