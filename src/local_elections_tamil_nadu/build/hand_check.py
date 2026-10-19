"""Draw a hand-check sample and crop each row's source region.

Ten seats per election (2011, 2019, 2021 ordinary), drawn with a fixed seed.
For each, the source page is rendered with pdftoppm and cropped from just
above the candidate table (where the panchayat heading is printed) down to
the winner's row (plus the foot of the previous page when the heading is
printed there). The crops go to data/checks/hand/ and the parsed values to
data/checks/hand_sample.csv. A person then reads each crop and records what
it says in data/checks/hand_check.csv (columns hand_*), which `make verify`
hashes.

Run: python -m local_elections_tamil_nadu.build.hand_check
"""

import subprocess

import pandas as pd

from local_elections_tamil_nadu.parse.common import DATA, ROOT

OUT = DATA / "checks" / "hand"
DPI = 110
SEED = 20261018


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for year in (2011, 2019, 2021):
        s = pd.read_parquet(DATA / str(year) / "vp_president_results.parquet")
        c = pd.read_parquet(DATA / str(year) / "vp_president_candidates.parquet")
        s = s[s["election_type"] == "General Election"]
        pick = s.sample(10, random_state=SEED)
        for i, seat in enumerate(pick.itertuples(), 1):
            w = c[
                (c["district_code"] == seat.district_code)
                & (c["block_seq"] == seat.block_seq)
                & c["elected"]
            ].iloc[0]
            _, _, x1, bottom = w["source_bbox"]
            y0 = max(w["table_top"] - 64, 0)
            scale = DPI / 72
            name = f"{year}_{i:02d}.png"
            subprocess.run(
                [
                    "pdftoppm",
                    "-f", str(w["source_page"]),
                    "-l", str(w["source_page"]),
                    "-r", str(DPI),
                    "-x", str(int(20 * scale)),
                    "-y", str(int(y0 * scale)),
                    "-W", str(int((x1 + 10) * scale)),
                    "-H", str(int((bottom - y0 + 4) * scale)),
                    "-png",
                    "-singlefile",
                    str(ROOT / w["source_path"]),
                    str(OUT / name[:-4]),
                ],
                check=True,
            )  # fmt: skip
            if int(seat.heading_page) != int(w["source_page"]):
                # heading at the foot of the previous page: crop its last 150 pt
                subprocess.run(
                    [
                        "pdftoppm",
                        "-f", str(seat.heading_page),
                        "-l", str(seat.heading_page),
                        "-r", str(DPI),
                        "-x", str(int(20 * scale)),
                        "-y", str(int(642 * scale)),
                        "-W", str(int((x1 + 10) * scale)),
                        "-H", str(int(150 * scale)),
                        "-png",
                        "-singlefile",
                        str(ROOT / w["source_path"]),
                        str(OUT / f"{name[:-4]}_heading"),
                    ],
                    check=True,
                )  # fmt: skip
            rows.append(
                {
                    "sample_id": name[:-4],
                    "year": year,
                    "district_code": seat.district_code,
                    "block": seat.block,
                    "gram_panchayat": seat.gram_panchayat,
                    "reservation_raw": seat.reservation_raw,
                    "winner": seat.winner,
                    "winner_sex_raw": w["sex_raw"],
                    "votes": seat.votes,
                    "source_path": w["source_path"],
                    "source_page": int(w["source_page"]),
                    "heading_on_same_page": int(seat.heading_page)
                    == int(w["source_page"]),
                    "crop": f"data/checks/hand/{name}",
                }
            )
    pd.DataFrame(rows).to_csv(DATA / "checks" / "hand_sample.csv", index=False)
    print(f"{len(rows)} crops in {OUT}")


if __name__ == "__main__":
    main()
