# Working on this data repository

This is a point-in-time data collection. Follow the [data-repository policy](https://github.com/soodoku/data-repos#maintenance-policy).

- Preserve sources, collection dates, provenance, schemas and reproducible parsing commands. Every fetched file is logged in `data/raw/fetch_log.csv` with its sha256 and fetch time; never overwrite one.
- Collection and parsing are separate. `make collect` is the only step that touches the network; `make data` reads only `data/raw/`.
- `make collect-tnsec` needs an Indian connection (tnsec.tn.gov.in refuses others); set `TN_PROXY` to a SOCKS5 proxy in India.
- Run `make check` once when code, inputs or outputs change. `make hand-sample` needs `pdftoppm` (poppler).
- Names are kept in Tamil, the script they were printed in. Do not transliterate in place; transliteration belongs in a derived file.
- The glyph tables in `parse/tamil_fonts.py` were read off the embedded font outlines. Add a glyph only after looking at it.
- Ask when source meaning or credentials are unclear. Never infer substantive data values to make a check pass.
