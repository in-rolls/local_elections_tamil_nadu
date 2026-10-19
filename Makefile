PY = .venv/bin/python
RUFF = .venv/bin/ruff

.PHONY: sync collect collect-tnsec collect-tnrd data hand-sample manifest lint verify check

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
	$(MAKE) manifest

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
