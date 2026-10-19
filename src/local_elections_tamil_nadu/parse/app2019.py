"""Parse the commission's 2019 results application (saved HTML only).

level_2/dNN.html  one row per union: posts in total, posts declared, posts
                  with no nomination; the "declared" cell links level_3.
level_3/dNN_bMM.html  one row per village panchayat: name, elected person as
                  "திரு <name>" (Mr) or "திருமதி <name>" (Mrs/Ms), result.

The application is a second, independently typed publication of the same
results as the PDFs: it gives the winner in Unicode with an honorific, but no
reservation. Outputs data/2019/app_union_counts.parquet and
data/2019/app_winners.parquet.

Run: python -m local_elections_tamil_nadu.parse.app2019
"""

import base64
import re

import pandas as pd
from bs4 import BeautifulSoup

from local_elections_tamil_nadu.parse.common import DATA, RAW, rel

APP = RAW / "tnsec" / "rlbe2019_app"
LINK = re.compile(r"dcode=([A-Za-z0-9=]+)&(?:amp;)?bcode=([A-Za-z0-9=]+)")
HONORIFIC = {"திருமதி": "female", "செல்வி": "female", "திரு": "male"}


def b64(code):
    return int(base64.b64decode(code).decode())


def soup(path):
    return BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")


def district_name(page):
    title = page.find("h5", class_="card-title").get_text(" ", strip=True)
    return title.split("-", 1)[1].strip()


def unions():
    rows = []
    for path in sorted((APP / "level_2").glob("d*.html")):
        page = soup(path)
        district = district_name(page)
        for tr in page.select("table.main-table tbody tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            link = tr.find("a", href=LINK)
            if not link or len(cells) < 4:
                continue
            dcode, bcode = LINK.search(link["href"]).groups()
            rows.append(
                {
                    "district_app_code": b64(dcode),
                    "district": district,
                    "union_app_code": b64(bcode),
                    "block": cells[0],
                    "posts_total": int(cells[1]),
                    "posts_declared": int(cells[2]),
                    "posts_no_nomination": int(cells[3]),
                    "source_path": rel(path),
                }
            )
    return pd.DataFrame(rows)


def winners(union_table):
    names = {
        (r.district_app_code, r.union_app_code): (r.district, r.block)
        for r in union_table.itertuples()
    }
    rows = []
    for path in sorted((APP / "level_3").glob("d*_b*.html")):
        d, b = (int(x) for x in re.findall(r"\d+", path.stem))
        district, block = names[(d, b)]
        page = soup(path)
        for i, tr in enumerate(page.select("table tr"), 1):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) != 3:
                continue
            gp, person, result = cells
            title, _, name = person.partition(" ")
            if title not in HONORIFIC:
                title, name = "", person
            rows.append(
                {
                    "district_app_code": d,
                    "district": district,
                    "union_app_code": b,
                    "block": block,
                    "gram_panchayat": gp,
                    "winner_printed": person,
                    "winner_honorific": title or None,
                    "winner": name.strip() or None,
                    "winner_gender_from_honorific": HONORIFIC.get(title),
                    "result": result,
                    "source_path": rel(path),
                    "source_row": i,
                }
            )
    return pd.DataFrame(rows)


def main():
    out = DATA / "2019"
    out.mkdir(parents=True, exist_ok=True)
    u = unions()
    w = winners(u)
    u.to_parquet(out / "app_union_counts.parquet", index=False)
    w.to_parquet(out / "app_winners.parquet", index=False)
    print(f"{len(u)} unions, {u.posts_total.sum()} posts; {len(w)} panchayat rows")
    print(w["result"].value_counts().to_string())
    print(w["winner_honorific"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
