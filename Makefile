PY = .venv/bin/python
RUFF = .venv/bin/ruff

.PHONY: sync collect collect-tnsec collect-tnrd data links union-evidence hand-sample manifest lint verify check

sync:
	uv sync --frozen --all-groups

# network; fetches only what data/raw/fetch_log.csv does not already hold
collect: collect-tnsec collect-tnrd

# needs an Indian connection: TN_PROXY (default socks5h://localhost:1080)
collect-tnsec:
	$(PY) -m local_elections_tamil_nadu.collect.tnsec

collect-tnrd:
	$(PY) -m local_elections_tamil_nadu.collect.tnrd

# reads only data/raw
data:
	$(PY) -m local_elections_tamil_nadu.parse.results
	$(PY) -m local_elections_tamil_nadu.parse.app2019
	$(PY) -m local_elections_tamil_nadu.parse.wards
	$(MAKE) manifest

# 2011 -> 2019/2021 seat links from the results tables and the hand-coded
# union crosswalk and review in data/linkage/
links:
	$(PY) -m local_elections_tamil_nadu.linkage.vp_links
	$(MAKE) manifest

# evidence table the union crosswalk was coded from (does not touch the crosswalk)
union-evidence:
	$(PY) -m local_elections_tamil_nadu.linkage.union_evidence

# redraws the crops for the hand check (needs pdftoppm)
hand-sample:
	$(PY) -m local_elections_tamil_nadu.build.hand_check

manifest:
	$(PY) -m local_elections_tamil_nadu.build.release write

lint:
	$(RUFF) check .
	$(RUFF) format --check .

verify:
	$(PY) -m local_elections_tamil_nadu.build.release verify

check: lint verify
	$(PY) -m unittest discover -s tests -v
