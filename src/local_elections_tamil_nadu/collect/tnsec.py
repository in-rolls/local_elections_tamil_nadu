"""Collect the commission's village panchayat president results. Needs India.

Two published forms, both read 2026-10-18 (see collect/fetch.py for the proxy):

1. Result sheets (PDF), tnsec_static/election_results/<election>/. The
   landing page <election>.php has a district <select>; POSTing
   cmb_district=<code> returns that district's page, which links
   vpp_<code>.pdf ("village panchayat president"). Each PDF prints, per
   village panchayat, its union, name and reservation, then every candidate
   with sex, father/husband name, votes, share and result. Elections:
     rulbe2011  ordinary election, October 2011 (31 rural districts)
     rlbe2019   ordinary election, December 2019 (27 districts)
     rlbe2021   ordinary election, October 2021, in the 9 districts left out
                in 2019, plus casual by-elections elsewhere
   The 2011 page also links state abstracts (counts by category), kept as
   an external check.

2. The 2019 results application, nomination/project_main/election_result/:
   village_panchayat_president_level_1 (districts), _level_2 (unions per
   district, with post counts), _level_3 (winner per village panchayat,
   honorific and name in Unicode). Codes are base64 in the query string.
   No such application exists for 2011 or 2021 (probed 2026-10-18).

Ward-member files are not collected. Every saved response is logged in
data/raw/fetch_log.csv; a logged path is not fetched again.

Run: python -m local_elections_tamil_nadu.collect.tnsec
"""

import base64
import logging
import re

from local_elections_tamil_nadu.collect.fetch import (
    ROOT,
    fetch,
    logged,
    session,
    setup_logging,
)

BASE = "https://tnsec.tn.gov.in"
RESULTS = f"{BASE}/tnsec_static/election_results"
APP = f"{BASE}/nomination/project_main/election_result"
OUT = "data/raw/tnsec"
ELECTIONS = ["rulbe2011", "rlbe2019", "rlbe2021"]
# Pages kept as survey evidence of what the site offers.
SITE = [
    "tnsec_static/election_results/election_results_t.php",
    "tnsec_static/election_results/rulbe2014/rulbe2014.php",
    "tnsec_static/election_results/rulbe2022/rulbe2022.php",
    "tnsec_static/header_and_footer_related/sitemap_t.php",
    "tnsec_static/elections/ele_reservation_e.php",
    "tnsec_static/statutory_orders/SO2019/SO2019.php",
    "tnsec_static/statutory_orders/SO2021/SO2021.php",
    "nomination/project_main/nomination_view/",
    "nomination_view_2021/",
]
OPTION = re.compile(r'<option value="([a-z]{3})">')
# Only the plain file names the pages use; anything else (e.g. "../") is ignored.
LINK = re.compile(r"window\.open\('((?:vpp|abstract)_[a-z_]+\.pdf)'")
LEVEL2 = re.compile(
    r"village_panchayat_president_level_2\.php\?post_code=MQ==&(?:amp;)?dcode=([A-Za-z0-9=]+)"
)
LEVEL3 = re.compile(
    r"village_panchayat_president_level_3\.php\?post_code=MQ==&(?:amp;)?"
    r"dcode=([A-Za-z0-9=]+)&(?:amp;)?bcode=([A-Za-z0-9=]+)"
)

log = logging.getLogger("tnsec")


def b64(code):
    """A dropdown/link id: base64 of a number. Only digits are accepted,
    since the id becomes part of a file name."""
    text = base64.b64decode(code).decode("ascii", "replace")
    if not re.fullmatch(r"[0-9]{1,4}", text):
        raise ValueError(f"unexpected id {code!r} -> {text!r}")
    return text


def text(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def site_pages(s, held):
    for page in SITE:
        name = page.strip("/").replace("/", "__")
        fetch(s, f"{BASE}/{page}", f"{OUT}/site/{name}.html", held=held)


def result_sheets(s, held):
    for election in ELECTIONS:
        url = f"{RESULTS}/{election}/{election}.php"
        landing = fetch(s, url, f"{OUT}/{election}/landing.html", held=held)
        page = landing.read_text(encoding="utf-8", errors="replace")
        districts = sorted(set(OPTION.findall(page)))
        log.info("%s: %d districts", election, len(districts))
        pdfs = {p for p in LINK.findall(page) if p.startswith("abstract_")}
        for d in districts:
            rel = f"{OUT}/{election}/district/{d}.html"
            path = fetch(
                s, url, rel, method="POST", data={"cmb_district": d}, held=held
            )
            linked = LINK.findall(path.read_text(encoding="utf-8", errors="replace"))
            vpp = [p for p in linked if p.startswith("vpp_")]
            if not vpp:
                log.warning("%s %s: no president file linked", election, d)
            pdfs.update(vpp)
        for name in sorted(pdfs):
            fetch(
                s, f"{RESULTS}/{election}/{name}", f"{OUT}/{election}/{name}", held=held
            )


def results_app(s, held):
    out = f"{OUT}/rlbe2019_app"
    top = fetch(
        s,
        f"{APP}/village_panchayat_president_level_1.php?post_code=MQ==",
        f"{out}/level_1.html",
        held=held,
    )
    dcodes = sorted(set(LEVEL2.findall(top.read_text(encoding="utf-8"))), key=b64)
    log.info("2019 app: %d districts", len(dcodes))
    for dcode in dcodes:
        d = b64(dcode)
        page = fetch(
            s,
            f"{APP}/village_panchayat_president_level_2.php?post_code=MQ==&dcode={dcode}",
            f"{out}/level_2/d{int(d):02d}.html",
            held=held,
        )
        for dc, bcode in sorted(set(LEVEL3.findall(page.read_text(encoding="utf-8")))):
            b = b64(bcode)
            fetch(
                s,
                f"{APP}/village_panchayat_president_level_3.php"
                f"?post_code=MQ==&dcode={dc}&bcode={bcode}",
                f"{out}/level_3/d{int(b64(dc)):02d}_b{int(b):02d}.html",
                held=held,
            )


def main():
    setup_logging(f"{OUT}/collect.log")
    s = session()
    held = None  # re-read the log on each call so a resumed run skips work
    site_pages(s, held)
    result_sheets(s, held)
    results_app(s, held)
    log.info("done; %d files logged", len(logged()))


if __name__ == "__main__":
    main()
