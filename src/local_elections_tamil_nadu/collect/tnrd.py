"""Collect the reservation gazettes held by the Rural Development department.

tnrd.tn.gov.in answers from outside India, so this connects directly. Its
"Panchayat Raj Reservation Gazette" index (dyn_json_schemes_name_details.php,
sch_code 58) lists eight gazettes, 1996-2011, and nothing later whatever year
is requested (checked 2026-10-18 for 2016, 2019, 2020, 2021). All eight are
kept, with the index page and the department's 2006 election summary page:

  395/1996, 401/1996  1996 reservation orders (scans)
  636/2001  2001 amendments to the 1996 president roster (scan)
  214/2006  2006 reservation order
  228/2006  G.O.Ms.107 president roster, 2006 (509-page scan, ~116 MB)
  254/2006  G.O.Ms.121 errata to 228/2006
  316/2011  2011 reservation order
  318/2011  G.O.Ms.60 de-reservations and G.O.Ms.61 president roster, 2011
  the index page and the department's 2006 election summary page

A file over GitHub's 100 MB limit (228/2006) is committed as byte-split parts,
`split -b 90m -a 1 FILE FILE.part_`; `cat FILE.part_*` restores it, and
`make verify` checks the parts against the logged sha256.

Run: python -m local_elections_tamil_nadu.collect.tnrd
"""

import logging

from local_elections_tamil_nadu.collect.fetch import (
    fetch,
    session,
    setup_logging,
)

OUT = "data/raw/tnrd"
GO = "https://tnrd.tn.gov.in/project/go_files"
FILES = {
    "index.html": "https://www.tnrd.tn.gov.in/dyn_json_schemes_name_details.php"
    "?go_type=MQ%3D%3D&n=bmV3&sch_code=NTg%3D&scheme_type=MQ%3D%3D&y=MjAxMQ%3D%3D",
    "panchayat_elections.html": "https://tnrd.tn.gov.in/panchayatraj_inst/"
    "panchayat_elections.html",
    "1_58_2011_318_en.pdf": f"{GO}/1_58_2011_318_en.pdf",
    "1_58_2006_254_en.pdf": f"{GO}/1_58_2006_254_en.pdf",
    "1_58_2006_228_en.pdf": f"{GO}/1_58_2006_228_en.pdf",
    "1_58_1996_395_en.pdf": f"{GO}/1_58_1996_395_en.pdf",
    "1_58_1996_401_en.pdf": f"{GO}/1_58_1996_401_en.pdf",
    "1_58_2001_636_en.pdf": f"{GO}/1_58_2001_636_en.pdf",
    "1_58_2006_214_en.pdf": f"{GO}/1_58_2006_214_en.pdf",
    "1_58_2011_316_en.pdf": f"{GO}/1_58_2011_316_en.pdf",
}

log = logging.getLogger("tnrd")


def main():
    setup_logging("data/search_log/tnrd_collect.log")
    s = session(proxy=False)
    for name, url in FILES.items():
        fetch(s, url, f"{OUT}/{name}")


if __name__ == "__main__":
    main()
