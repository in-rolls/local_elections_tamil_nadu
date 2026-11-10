# Chennai and Coimbatore urban election sources

Collected November 9, 2026 UTC. The handoff retains the best available candidate results, dated primary reservation and boundary documents, and explicit source limitations. No effects or cross-election ward links are estimated.

| City and election | Candidates | Winners | Recorded winner sex | Reservation |
|---|---:|---:|---|---|
| Chennai 2011 | 2,472 | 200 | Missing | Missing |
| Chennai 2022 | 2,670 | 200 | 101 Female, 99 Male | Primary gazette: 100 women-reserved |
| Coimbatore 2022 | 778 | 100 | 55 Female, 45 Male | Secondary SEC extraction: 50 women-reserved |

The typed files are `data/release/urban/candidates.parquet` (one candidate per year, body, ward and printed candidate serial) and `winners.parquet` (one elected candidate per year, body and ward). The adjacent `dictionary.csv` defines every column in all five tables. The two CSV source extracts for Coimbatore district also contain municipalities and town panchayats; only election ID `TNULB-2022-CORP-CBE-01` enters this corporation handoff. The original district CSVs are retained once.

## Sources and handling

**2022 candidate results.** Tamil Nadu Data's downloadable [Chennai](https://www.tamilnadudata.org/elections/local-body/district/chn/) and [Coimbatore](https://www.tamilnadudata.org/elections/local-body/district/cbe/) tables describe extraction from the SEC's `corp_chn.pdf` and `corp_cbe.pdf`. The retained CSVs include Tamil names, printed candidate serials, sex, party, votes and election status. These are secondary extracts of official results, not retained primary result PDFs. The source gender values are preserved: Male/Female map to the corresponding indicator; three Chennai candidates recorded as Transgender retain that label and a null woman indicator. No sex is inferred from name, reservation or photograph. No winner is selected merely by taking the maximum votes: the published result status identifies the winner. Candidate and ward tables agree on all 300 winner names, parties and votes; this is an internal check of the same secondary publication, not independent verification.

**2011 Chennai results.** The [LiveChennai result republication](https://www.livechennai.com/Councillors_Chennai.asp) explicitly identifies the 2011 election and supplies every candidate's name, party, votes and declared status for wards 1–200. It lacks sex and reservation. Those values remain null. Its Tamil names are preserved, without transliteration or inferred sex. The source has one elected candidate per ward and unique ward/candidate serials. Primary confirmation remains outstanding.

**Chennai reservation.** The adopted 2022 treatment comes from [Gazette 46, January 17, 2022](https://chennaicorporation.gov.in/gcc/delimited_ward/pdf/46_Ex_VI_2.pdf-for-Author.pdf), retained as `chennai_reservation_2022.pdf`. Pages 2–4 list 16 SC-general, 16 SC-women and 84 general-women wards. The remaining 84 wards are unreserved. Primary rows and pages are exported separately. The secondary ward extract incorrectly labels **wards 183 and 185 as general rather than general-women**. The printed gazette's page 4, serials 79 and 80, was visually inspected. The output adopts the gazette and preserves the secondary text and a conflict flag. This changes the women-reserved count from 98 to 100; it does not change winner sex.

**Coimbatore councilor list.** The official [CCMC 2022 PDF](https://www.ccmc.gov.in/img/upload/CCMC-Councilors%20Details%202022.pdf) contains all 100 councilor names and parties. Its PDF metadata reports creation and modification on March 14, 2022. Names and parties are parsed with PDF page references into a separate Parquet table and attached to the corresponding 2022 ward rows as primary source fields. The PDF's English names and the secondary table's Tamil names are not treated as exact name matches; no complete independent identity-validation claim is made. The PDF contains photographs but no sex column. Sex is not derived from those photographs. Addresses, telephone numbers and email addresses remain only in the unchanged original PDF and are not added to the analytical export.

**Additional retained comparison.** The [OpenCity Chennai dataset](https://data.opencity.in/dataset/chennai-gcc-elections-data-2022), its CKAN metadata and CSV are preserved as a separate source. Despite its “Results” title, the CSV has candidate name, sex, age, party and reservation but no vote/result-status field. It is not substituted for the winner list, and no unverified English/Tamil name join is performed.

## Boundaries and remaining source questions

Chennai's [December 14, 2018 delimitation gazette](https://chennaicorporation.gov.in/gcc/delimited_ward/pdf/2018_delimitation.pdf) explicitly supersedes the earlier ward notification and provides 206 pages of ward extents. The [July 19, 2011 document](https://www.tniuscbe.org/download/gg11/gg2/11egg226.pdf) is titled a proposal for delimitation and is retained as historical boundary evidence, not certified as the final 2011 crosswalk. Equal counts of 200 wards do not establish continuity between 2011 and 2022. Every winner row explicitly marks geographic linkage unvalidated. No historical Coimbatore crosswalk is claimed.

The SEC's 2011 and 2022 result PDF endpoints timed out from this connection. The repository documents the need for an India connection; no `TN_PROXY` was configured. Four exact-URL archive searches found one Chennai 2011 capture (April 12, 2024), but replay returned HTTP 429 and was not retained as a PDF. The other three queries returned no captures; this is not evidence that no archive holds them. Requests, failures and replay status are documented in [acquisition_attempts.json](../../search_log/urban/acquisition_attempts.json), [archive_checks.json](../../search_log/urban/archive_checks.json) and [archive_replay.json](../../search_log/urban/archive_replay.json). Coimbatore 2011 and both cities' 2006 candidate results were not recovered in this pass.

The Chennai 2022 source yields 101 women, consistent with one [contemporaneous report](https://www.newindianexpress.com/amp/story/good-news/2022/Mar/03/chennai-gets-new-councillors-after11-years-women-outnumber-men-2425681.html); other contemporaneous reports give 102. No source value is changed to force agreement with an aggregate news figure. Primary candidate-level sex confirmation remains preferable.

## Reproduction and receipts

`data/raw/fetch_log.csv` pins every retained original response with URL, acquisition time, byte count and SHA-256; the 2011 HTML is losslessly gzipped. `data/manual/urban/sources.csv` is the manually enumerated collection frame. The collector resumes from existing receipts and does not overwrite held files. The parser reads retained files only and verifies all inputs it uses. No copy of these originals is placed in the manuscript repository.

```sh
PYTHONPATH=src python -m local_elections_tamil_nadu.collect.urban
PYTHONPATH=src python -m local_elections_tamil_nadu.parse.urban
PYTHONPATH=src python -m pytest -q tests/test_urban.py
```

The first command uses the network; the remaining commands are offline. The release includes source-level reservation and councilor tables, a discrepancy report, schema, coverage counts and output hashes. Focused tests check source changes, incomplete frames, primary reservation corrections, source rows, unknown sex and deterministic rebuilding. The existing rural releases are unchanged.


## Published table contracts

The five analytical tables are Parquet, compressed with Zstandard:
`candidates.parquet`, `winners.parquet`, `chennai_reservations_2022.parquet`,
`coimbatore_councilors_2022.parquet`, and `reserved_source_conflicts.parquet`.
No CSV aliases of these tables are retained. Raw CSV downloads remain unchanged.

`schema.json` declares each table's fields, physical Arrow types, nullability,
allowed values, row unit, expected count and primary key. The parser validates
these contracts before writing; Parquet round trips are checked. `dictionary.csv`
covers every table/column pair, including unavailable values and source meanings.
`checksums.json` pins all parser-produced tables and metadata. The repository's
existing `data/MANIFEST.json` now also pins the urban release, and `make check`
validates its schemas, keys, dictionaries, indicator semantics and output hashes.

Identifiers `ward_no` and `candidate_no` are strings. `year` is an integer.
`candidate_woman`, `winner_woman` and `reserved_woman` use nullable Int8 values
1/0/null; missing or other recorded sex is never converted to zero. Candidate
and winner columns use the same vocabulary as `local_elections/docs/naming.md`.
Winner sex comes from the published elected candidate row, with that basis
explicit. Councilor-list joins retain their separate fields and join basis;
they do not overwrite the recorded winner or sex. Unknown 2011 reservation and
sex values remain null. This source-specific supplement does not invent pooled
record IDs, source commits, districts or unavailable reservation values.

[renames.csv](../../manual/urban/renames.csv) records the old and new field/path
names. Every previously exported candidate and winner cell was compared before
and after migration: the 5,920 candidates and 500 winners retain the same values,
with only documented names and storage types changed.
