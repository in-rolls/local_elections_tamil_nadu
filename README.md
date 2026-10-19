# Tamil Nadu village panchayat president elections, 2011, 2019 and 2021

One row per village panchayat president seat (கிராம ஊராட்சித் தலைவர்) in
Tamil Nadu's ordinary rural elections of October 2011, December 2019 (27
districts) and October 2021 (the nine districts left out in 2019). Each row
carries:

- the seat's reservation (SC / ST / general, woman or not);
- the winner, with sex as printed;
- every candidate's votes;
- the page, table and row of the commission's result sheet it was read from.

Built for linking panchayats across consecutive elections, to study whether a
women's quota in one term changes who wins the open seat in the next. **The
cross-election link is not built here**; see
[Linking across elections](#linking-across-elections).

## Data

| File | Unit |
|---|---|
| `data/2011/vp_president_results.parquet` | seat, 31 rural districts (12,523) |
| `data/2011/vp_president_candidates.parquet` | candidate |
| `data/2019/vp_president_results.parquet` | seat, 27 districts (9,624, of which 2 had no nomination) |
| `data/2019/vp_president_candidates.parquet` | candidate |
| `data/2021/vp_president_results.parquet` | seat: nine districts' ordinary election (`election_type` = `General Election`) plus casual by-elections elsewhere (`By Election`) |
| `data/2021/vp_president_candidates.parquet` | candidate |
| `data/2019/app_winners.parquet` | panchayat row in the commission's 2019 results application, a second publication of the same results (winner with honorific) |
| `data/2019/app_union_counts.parquet` | union: posts in total, declared, without nomination |
| `data/checks/hand_check.csv`, `data/checks/hand/` | 30 sampled rows read by hand against crops of the source |
| `data/reference/` | district codes; the mPDF glyph table; seat counts from the 2011 gazette roster |

`data/MANIFEST.json` holds the sha256 of every output and the result of every
check.

### Seat columns

Names follow the pooled schema (`local_elections`, `schemas/master.json`);
candidate files follow `schemas/candidates.json`.

| Column | Meaning |
|---|---|
| `year`, `election`, `election_type` | 2011, 2019 or 2021; the source folder (`rulbe2011`, `rlbe2019`, `rlbe2021`); `General Election` or `By Election` |
| `district_code` | the commission's three-letter code; `data/reference/districts.csv` names them |
| `block` | panchayat union (ஊராட்சி ஒன்றியம்) as printed, Tamil |
| `gram_panchayat` | village panchayat as printed, Tamil |
| `block_seq` | order of the panchayat within its district file |
| `reservation_raw` | the bracket as printed: பொது (general), ஆதி திராவிடர் (SC), பழங்குடியினர் (ST), followed by (பெண்கள்) "women" or (பொது) "general" |
| `caste_reservation`, `woman_reserved`, `reservation` | the bracket folded: `NONE`/`SC`/`ST`; true/false; the pooled label (`SC Woman`, `Other than Woman`, ...). Left empty when the bracket is printed empty |
| `electors`, `votes_polled`, `valid_votes`, `rejected_votes` | as printed above each table |
| `seat_candidates` | candidates listed |
| `winner`, `winner_relation_name` | elected person and father's/husband's name, Tamil, as printed |
| `winner_gender`, `winner_woman` | **recorded** sex: the sheet's பாலினம் column (ஆண் male, பெண் female, மற்றவர் other). Never inferred from a name. Not in the pooled master schema; it mirrors `candidate_gender` in the candidates schema |
| `winner_basis` | `published`, `uncontested` (போட்டியின்றி தேர்வு), or `lot` (வெற்றி (குலுக்கல் முறை): a tie broken by drawing lots) |
| `votes`, `runner_up`, `runner_up_votes`, `margin` | the winner's votes and the best loser's |
| `unopposed`, `vacant` | elected unopposed; no one elected (a heading printed with no candidate) |
| `source_path`, `source_page`, `heading_page`, `heading_raw` | file under `data/raw/`, page of the winner's row, page and text of the panchayat heading |
| `quality_flags` | `reservation_blank_in_source`, `no_candidates_printed` |

Candidate files add `candidate_no`, `candidate_name`, `relation_name`,
`sex_raw`, `candidate_gender`, `votes`, `vote_pct`, `result` (as printed:
வெற்றி won, தோல்வி lost, வைப்புத்தொகை இழப்பு lost deposit, போட்டியின்றி
தேர்வு unopposed), `elected`, `source_table`, `source_row` and `source_bbox`
(PDF points, top-left origin).

Names stay in Tamil script. Some 2019 and 2021 names were keyed by the
commission with ா in place of ர (e.g. மாாியம்மாள் for மாரியம்மாள்); they are
kept as printed, and the checks fold them only for comparison.

## Sources, and what exists by year

All the results are in Tamil. The English pages of the commission's site say
"please see in Tamil version". The survey was done on 2026-10-18 through a
proxy in Mumbai, because tnsec.tn.gov.in refuses connections from outside
India.

| Year | What exists | Collected |
|---|---|---|
| 2006 | **Reservation roster:** Gazette 228/2006 (G.O.Ms.107), a 509-page scan, and its errata, Gazette 254/2006, both on tnrd.tn.gov.in. TNRD's summary page gives 12,618 president posts, 4,275 of them reserved for women. **No per-panchayat results found.** The commission's results page starts at 2011, and Wayback captures of the old site (tnsec.tn.nic.in, 2006-2011) hold only union and district tier pages | 254/2006. 228/2006 is hashed and listed in `data/raw/LARGE_FILES.csv` (116 MB) |
| 2011 | **Results:** one PDF per district, `tnsec_static/election_results/rulbe2011/vpp_<code>.pdf`, with every candidate's sex and votes and the reservation in each heading. **State abstracts** by category. **Reservation roster:** Gazette 318/2011 (G.O.Ms.61) | all 31 rural district PDFs, 8 abstracts, Gazette 318 |
| 2014, 2022 | Casual (by-)election results, in the same layout | landing pages only |
| 2019 | **Results PDFs:** `rlbe2019/vpp_<code>.pdf` (27 districts). **Results application:** `nomination/project_main/election_result/`, with the winner per panchayat in Unicode, with honorific. **No reservation roster online:** TNRD's gazette index stops at 2011, and the 2016 notification that set the counts (II(2)/RDPR/640(a-1)/2016) is cited but not online | all 27 PDFs; application levels 1-3 |
| 2021 | **Results PDFs:** `rlbe2021/vpp_<code>.pdf`, covering the ordinary election in 9 districts plus casual elections in others. No results application | every district PDF linked |

`data/raw/fetch_log.csv` records the URL, method, sha256, size, HTTP status
and UTC time of every saved response. The `collect.log` files record each
run.

## How the text was recovered

Ordinary text extraction garbles these PDFs, differently by year. The fixes
are in `parse/tamil_fonts.py`:

- **2019 and 2021** (made with mPDF 5.7.4). mPDF writes each character as its
  own code point, with two exceptions. Pre-base vowel signs (ெ ே ை) are moved
  in front of their consonant. Conjuncts and consonant-vowel ligatures are
  replaced by Private Use Area codes. The PUA table is mPDF's own
  (`includes/ind_ta_1_001.volt.php`, vendored in `data/reference/`).
  Inverting it and moving the vowels back restores the Unicode exactly.
- **2011** (Windows printer driver, then Ghostscript). Each file embeds
  subsets of the Latha font. Some glyphs are named by code point
  (`uni0B95_uni0BC1`); others carry a bare index (`g132`) or a private name
  (`tm_r_ikaar`). The 70 bare and private names were labelled by rendering
  their outlines from the embedded fonts and reading them. A decoded 2011
  name is only as good as that table. The checks count names containing a
  sequence that Tamil cannot have.

Cells are read from the tables' rulings, not from line text, because long
names and the result column wrap onto two lines.

## Checks

`make check` runs lint and `build/release.py verify`, which recomputes every
check and every output hash. The table below is rewritten by `make
manifest`.

<!-- checks:start -->
| Check | Against | Result | Numbers |
|---|---|---|---|
| `2011_one_winner_per_seat`: each seat has exactly one candidate marked won or elected unopposed | internal | **pass** | {"seats": 12523, "flagged": 0} |
| `2011_reservation_read`: every seat's bracketed reservation maps to SC/ST/general x woman or not; brackets printed empty are left unknown and counted separately | internal | **pass** | {"unread": 0, "blank_in_source": 4} |
| `2011_votes_add_up`: candidate votes sum to the printed valid votes (catches dropped rows) | internal | **pass** | {"contested": 12175, "mismatched": 0} |
| `2011_glyphs_and_sex_decoded`: no undecoded glyph in names; every candidate's printed sex recognised; few names with a sequence Tamil cannot have (misordered glyphs) | internal | **warn** | {"undecoded": 0, "misordered_names": 50, "names_with_source_keying": 905, "sex_unread": 0} |
| `2011_winner_has_most_votes`: the candidate marked won has at least the runner-up's votes | internal | **pass** | {"exceptions": 0} |
| `2019_one_winner_per_seat`: each seat has exactly one candidate marked won or elected unopposed | internal | **pass** | {"seats": 9624, "flagged": 0} |
| `2019_reservation_read`: every seat's bracketed reservation maps to SC/ST/general x woman or not; brackets printed empty are left unknown and counted separately | internal | **pass** | {"unread": 0, "blank_in_source": 0} |
| `2019_votes_add_up`: candidate votes sum to the printed valid votes (catches dropped rows) | internal | **warn** | {"contested": 9212, "mismatched": 1} |
| `2019_glyphs_and_sex_decoded`: no undecoded glyph in names; every candidate's printed sex recognised; few names with a sequence Tamil cannot have (misordered glyphs) | internal | **pass** | {"undecoded": 0, "misordered_names": 19, "names_with_source_keying": 4852, "sex_unread": 0} |
| `2019_winner_has_most_votes`: the candidate marked won has at least the runner-up's votes | internal | **pass** | {"exceptions": 0} |
| `2021_one_winner_per_seat`: each seat has exactly one candidate marked won or elected unopposed | internal | **pass** | {"seats": 3005, "flagged": 0} |
| `2021_reservation_read`: every seat's bracketed reservation maps to SC/ST/general x woman or not; brackets printed empty are left unknown and counted separately | internal | **pass** | {"unread": 0, "blank_in_source": 0} |
| `2021_votes_add_up`: candidate votes sum to the printed valid votes (catches dropped rows) | internal | **pass** | {"contested": 2865, "mismatched": 0} |
| `2021_glyphs_and_sex_decoded`: no undecoded glyph in names; every candidate's printed sex recognised; few names with a sequence Tamil cannot have (misordered glyphs) | internal | **pass** | {"undecoded": 0, "misordered_names": 5, "names_with_source_keying": 782, "sex_unread": 0} |
| `2021_winner_has_most_votes`: the candidate marked won has at least the runner-up's votes | internal | **pass** | {"exceptions": 0} |
| `2011_seats_vs_sec_abstract`: seats parsed vs the commission's abstract: 12,524 posts, 12,523 filled | external | **pass** | {"parsed": 12523, "sec_posts": 12524, "sec_elected": 12523} |
| `2011_women_reserved_vs_sec_abstract`: women-reserved seats by caste category vs abstract_women.pdf; seats whose bracket is printed empty cannot be counted and may explain a gap | external | **warn** | {"parsed": {"ST": 38, "SC": 1164, "NONE": 3085}, "sec": {"ST": 38, "SC": 1164, "NONE": 3089}, "blank_in_source": 4} |
| `2011_winners_by_sex_vs_sec_abstract`: winners by printed sex vs abstract_categorywise.pdf (whose categories are the winners' own caste, not the seat's: it counts 4,077 SC winners against 3,132 SC-reserved seats, so only the sex totals are comparable) | external | **pass** | {"parsed_vs_sec": {"female": [4984, 4984], "male": [7539, 7539]}, "total_abs_gap": 0} |
| `2011_district_category_counts_vs_gazette_318`: seats per district x reservation in the results vs the September 2011 GO61 roster (Gazette 318, parsed independently in local_elections); differences can be real (later amendments, no-nomination seats) | external | **warn** | {"cells": 147, "cells_differing": 12, "seats_differing": 12, "examples": [{"cell": "ari/ST/False", "gazette": 3, "results": 2}, {"cell": "kar/SC/False", "gazette": 22, "results": 21}, {"cell": "nlg/NONE/False", "gazette": 13, "results": 14}, {"cell": "nlg/NONE/True", "gazette": 10, "results": 9}, {" |
| `2011_women_reserved_share`: 2011 reserved one third of offices for women (50% came in 2016) | legal | **pass** | {"share": 0.3424} |
| `2019_seats_vs_results_application`: seats in the PDFs (including headings printed with no candidate) vs posts in the commission's results application; the application's other rows are panchayats it marks 'result not declared' | external | **pass** | {"parsed": 9624, "parsed_no_candidates": 2, "app_posts": 9624, "app_posts_no_nomination": 2, "app_rows": 9690} |
| `2019_winner_vs_results_application`: PDF winner vs the application's winner for the same union and panchayat (two separately typed publications); sex compares printed sex with the application's honorific (திரு/திருமதி) | external | **pass** | {"seats": 9624, "joined_on_names": 9624, "winner_name_agree": 0.9995, "sex_compared": 9622, "sex_agree": 1.0} |
| `2019_women_reserved_share`: at least half of president offices reserved for women (Tamil Nadu Panchayats (Amendment) Act, 2016, L.A. Bill 5 of 2016, s.57), statewide and per district | legal | **pass** | {"share": 0.5, "districts_below_half": {}} |
| `2021_ordinary_seats_vs_sec`: seats in the nine districts' files vs the 2,901 posts announced | external | **warn** | {"parsed": 2900, "sec": 2901, "casual_seats": 105} |
| `2021_unopposed_vs_sec`: presidents elected unopposed in the nine districts vs 119 reported | external | **pass** | {"parsed": 119, "sec": 119} |
| `2021_women_reserved_share`: at least half of president offices reserved for women (Tamil Nadu Panchayats (Amendment) Act, 2016, L.A. Bill 5 of 2016, s.57), statewide and per district | legal | **pass** | {"share": 0.5003, "districts_below_half": {}} |
<!-- checks:end -->

What the passes rest on:

- **2011.** The 12,523 seats and the winners' sex totals (4,984 women, 7,539
  men) match the commission's own abstracts exactly. The abstracts were
  printed separately from the district sheets.
- **2019.** Two publications agree. The 2019 winners match the commission's
  separately typed results application on name for 99.98% of seats and on sex
  (printed sex against the honorific திரு/திருமதி) for all seats compared.
- **Reservation.** The 2011 reservation counts match the September 2011
  gazette roster in all but 12 district-by-category cells (12 seats). That
  roster was parsed independently, from English, in `local_elections`.

## Linking across elections

Not done here. What a link will rest on:

- **No shared code.** No file carries a statewide panchayat code, so a link
  must go through (union, panchayat name). The names are Tamil in all three
  years. Exact (union, panchayat) keys already match 88% of 2019/2021 seats to
  a 2011 seat; the panchayat name alone matches 94%.
- **New districts.** Districts were split after 2011: Kallakurichi from
  Villupuram, Chengalpattu from Kancheepuram, Tenkasi from Tirunelveli,
  Tirupathur and Ranipet from Vellore, and Mayiladuthurai from Nagapattinam.
  Match on union and panchayat, not on district.
- **Two-term gap.** 2011 to 2019 spans two terms, because the 2016 election
  was cancelled.
- **Quota levels differ.** In 2006 and 2011 one third of president offices
  were reserved for women (2011: 4,291 of 12,524). The Tamil Nadu Panchayats
  (Amendment) Act, 2016 (L.A. Bill 5 of 2016; section 57 for president offices) raised it to half, so 2019 and 2021 reserve 50%.
- **Rotation.** TNRD notes that reserved president offices were rotated after
  ten years for 2006 (G.O.Ms.105/2006). Whether 2011 kept the 2006 roster can
  be checked from Gazettes 228 and 318, but has not been checked.

## Reproduce

```
make sync
make collect      # network; tnsec.tn.gov.in needs TN_PROXY
make data         # parse data/raw into data/<year>/; rewrite the manifest
make check
```
