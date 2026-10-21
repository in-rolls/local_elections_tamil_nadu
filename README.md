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
women's quota in one term changes who wins the open seat in the next. The
2011 → 2019/2021 seat links are in `data/linkage/`; see
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
| `data/2011/ward_results.parquet` | ward, three rural offices (`tier`: `vp_ward` village panchayat 99,322; `pu_ward` panchayat union 6,471; `dp_ward` district panchayat 655). 2011 prints winners only for village wards, with the winner's community (`winner_community_raw`) |
| `data/2019/ward_results.parquet`, `data/2021/ward_results.parquet` | ward, the same three offices (2019: 76,734 / 5,090 / 515; 2021: 23,210 / 1,421 / 153, ordinary and by-elections) |
| `data/2011/ward_candidates.parquet`, `data/2019/ward_candidates.parquet`, `data/2021/ward_candidates.parquet` | candidate, with sex, votes, result, and party for union/district offices; 2011 has 36,250 union/district candidates and no village-candidate table |
| `data/2019/app_winners.parquet` | panchayat row in the commission's 2019 results application, a second publication of the same results (winner with honorific) |
| `data/2019/app_union_counts.parquet` | union: posts in total, declared, without nomination |
| `data/checks/hand_check.csv`, `data/checks/hand/` | 30 sampled rows read by hand against crops of the source |
| `data/linkage/vp_2011_2019.parquet`, `vp_2011_2021.parquet` | a 2011 seat paired with its 2019 or 2021 seat |
| `data/linkage/union_crosswalk_2011_2019_2021.csv`, `review_2011_2019_2021.csv` | the hand-coded union crosswalk and the hand review behind the links |
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
| `reserved_raw` | the bracket as printed: பொது (general), ஆதி திராவிடர் (SC), பழங்குடியினர் (ST), followed by (பெண்கள்) "women" or (பொது) "general" |
| `reserved_caste`, `reserved_woman`, `reserved_label` | the bracket folded: `NONE`/`SC`/`ST`; true/false; the pooled label (`SC Woman`, `Other than Woman`, ...). Left empty when the bracket is printed empty |
| `electors`, `votes_polled`, `valid_votes`, `rejected_votes` | as printed above each table |
| `seat_candidates` | candidates listed |
| `winner`, `winner_relation_name` | elected person and father's/husband's name, Tamil, as printed |
| `winner_woman`, `winner_woman_raw` | **recorded** sex: 1 woman, 0 man, blank for மற்றவர் (other) or unread; and the sheet's பாலினம் cell as printed (ஆண், பெண், மற்றவர்). Never inferred from a name. Mirrors `candidate_woman`, `candidate_woman_raw` in the candidates files |
| `winner_basis` | `published`, `uncontested` (போட்டியின்றி தேர்வு), or `lot` (வெற்றி (குலுக்கல் முறை): a tie broken by drawing lots) |
| `votes`, `runner_up`, `runner_up_votes`, `margin` | the winner's votes and the best loser's |
| `unopposed`, `vacant` | elected unopposed; no one elected (a heading printed with no candidate) |
| `source_path`, `source_page`, `heading_page`, `heading_raw` | file under `data/raw/`, page of the winner's row, page and text of the panchayat heading |
| `quality_flags` | `reservation_blank_in_source`, `no_candidates_printed` |

Candidate files add `candidate_no`, `candidate_name`, `relation_name`,
`candidate_woman_raw` (பாலினம் as printed), `candidate_woman` (1/0, blank for other), `votes`, `vote_pct`, `result` (as printed:
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
| 2006 | **Reservation roster:** Gazette 228/2006 (G.O.Ms.107), a 509-page scan, and its errata, Gazette 254/2006, both on tnrd.tn.gov.in. TNRD's summary page gives 12,618 president posts, 4,275 of them reserved for women. **No per-panchayat results found.** The commission's results page starts at 2011, and Wayback captures of the old site (tnsec.tn.nic.in, 2006-2011) hold only union and district tier pages | 254/2006. 228/2006 (116 MB, over GitHub's file limit) is committed as byte-split parts, `1_58_2006_228_en.pdf.part_a`/`part_b`; `cat` them to restore it |
| 2011 | **Results:** one PDF per district, `tnsec_static/election_results/rulbe2011/vpp_<code>.pdf`, with every candidate's sex and votes and the reservation in each heading. **State abstracts** by category. **Reservation roster:** Gazette 318/2011 (G.O.Ms.61) | all 31 rural district PDFs, 8 abstracts, Gazette 318 |
| 2014, 2022 | Casual (by-)election results, in the same layout | landing pages only |
| 2019 | **Results PDFs:** `rlbe2019/vpp_<code>.pdf` (27 districts). **Results application:** `nomination/project_main/election_result/`, with the winner per panchayat in Unicode, with honorific. **No reservation roster online:** TNRD's gazette index stops at 2011, and the 2016 notification that set the counts (II(2)/RDPR/640(a-1)/2016) is cited but not online | all 27 PDFs; application levels 1-3 |
| 2021 | **Results PDFs:** `rlbe2021/vpp_<code>.pdf`, covering the ordinary election in 9 districts plus casual elections in others. No results application | every district PDF linked |

`data/raw/fetch_log.csv` records the URL, method, sha256, size, HTTP status
and UTC time of every saved response. The `collect.log` files record each
run.

## Ward members

`parse/wards.py` reads the rural ward-member sheets (`vpwm_`, `puwm_`,
`dpwm_` in `data/raw/tnsec/<election>/`; village sheets are one per union from
2019). 2019 and 2021 print a heading per ward (`வார்டு எண்: N
[reservation]`) and every candidate; 2011 prints every candidate for union and
district wards but only the winners for village wards. The reservation in the
bracket is the ward's, read as for the presidents (with `ஆதிதிராவிடர்`,
printed without its space on 310 wards in 2011, read as SC).

Against the 2011 category-wise abstract: 655 of 655 district, 6,471 of 6,471
union and 99,322 of 99,324 village wards; village winners by community and
sex match the abstract in every cell but two. In 2019 and 2021 every ward with
candidates has exactly one winner; 41 and 26 wards print no candidate.

The 2011 village sheets contain 26 repeated district/union/panchayat/ward
keys after recovering the union headings from merged table cells in
Kanchipuram. They are retained with source page/table/row coordinates; the
printed place and ward fields are not a unique identifier. For example,
Cuddalore page 119 prints the same village and ward number for two rows.
The two-seat shortfall against the 2011 abstract is reported as a warning,
not exact agreement.

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
| `2011_district_category_counts_vs_gazette_318`: seats per district x reservation in the results vs the September 2011 GO61 roster (Gazette 318, parsed independently in local_elections); differences can be real (later amendments, no-nomination seats) | external | **warn** | {"cells": 147, "cells_differing": 12, "seats_differing": 12, "examples": [{"cell": "ari/ST/0", "gazette": 3, "results": 2}, {"cell": "kar/SC/0", "gazette": 22, "results": 21}, {"cell": "nlg/NONE/0", "gazette": 13, "results": 14}, {"cell": "nlg/NONE/1", "gazette": 10, "results": 9}, {"cell": "slm/NON |
| `2011_women_reserved_share`: 2011 reserved one third of offices for women (50% came in 2016) | legal | **pass** | {"share": 0.3424} |
| `2019_seats_vs_results_application`: seats in the PDFs (including headings printed with no candidate) vs posts in the commission's results application; the application's other rows are panchayats it marks 'result not declared' | external | **pass** | {"parsed": 9624, "parsed_no_candidates": 2, "app_posts": 9624, "app_posts_no_nomination": 2, "app_rows": 9690} |
| `2019_winner_vs_results_application`: PDF winner vs the application's winner for the same union and panchayat (two separately typed publications); sex compares printed sex with the application's honorific (திரு/திருமதி) | external | **pass** | {"seats": 9624, "joined_on_names": 9624, "winner_name_agree": 0.9994, "sex_compared": 9622, "sex_agree": 1.0} |
| `2019_women_reserved_share`: at least half of president offices reserved for women (Tamil Nadu Panchayats (Amendment) Act, 2016, L.A. Bill 5 of 2016, s.57), statewide and per district | legal | **pass** | {"share": 0.5, "districts_below_half": {}} |
| `2021_ordinary_seats_vs_sec`: seats in the nine districts' files vs the 2,901 posts announced | external | **warn** | {"parsed": 2900, "sec": 2901, "casual_seats": 105} |
| `2021_unopposed_vs_sec`: presidents elected unopposed in the nine districts vs 119 reported | external | **pass** | {"parsed": 119, "sec": 119} |
| `2021_women_reserved_share`: at least half of president offices reserved for women (Tamil Nadu Panchayats (Amendment) Act, 2016, L.A. Bill 5 of 2016, s.57), statewide and per district | legal | **pass** | {"share": 0.5003, "districts_below_half": {}} |
| `links_keys_resolve_one_to_one`: each link side's (district_code, block, gram_panchayat) names exactly one row of its results table (2021: ordinary election rows), and no seat is linked twice | internal | **pass** | {"2019:2011": {"repeated_in_links": 0, "not_one_row": 0}, "2019:2019": {"repeated_in_links": 0, "not_one_row": 0}, "2021:2011": {"repeated_in_links": 0, "not_one_row": 0}, "2021:2021": {"repeated_in_links": 0, "not_one_row": 0}} |
| `links_union_crosswalk_covers_all_unions`: every 2011 and later panchayat union appears in a usable crosswalk row | internal | **pass** | {"decisions": {"same": 368, "split": 27, "merged": 4, "uncertain": 1}, "unions_2011_uncovered": [], "unions_later_uncovered": []} |
| `links_precision_hand_review`: hand review (data/linkage/review_2011_2019_2021.csv; unsure counts as wrong): precision at least 98% in every stratum and overall. Fuzzy links were read in full, exact links by sample | external | **pass** | {"bands": {"exact": "76/76 of 11604, CI 0.9519-1.0", "exact_respelled": "45/45 of 368, CI 0.9213-1.0", "0.94-0.97": "256/259 of 259, CI 0.9665-0.9961", "0.97-1.00": "7/7 of 7, CI 0.6457-1.0"}, "estimate": 0.9998, "lower_bound": 0.9511} |
| `links_share_candidates_vs_random`: linked pairs share a candidate name across the two elections far more often than random pairs in the same union group (code shares nothing with the name match); exact and fuzzy links each at least ten times the random rate | external | **pass** | {"linked_exact": 0.1088, "linked_fuzzy": 0.0865, "random_same_union_group": 0.0012} |
| `2011_dp_ward_seats_vs_abstract`: rural ward seats in the 2011 sheets vs the commission's category-wise abstract | external | **pass** | {"parsed": 655, "published": 655} |
| `2011_pu_ward_seats_vs_abstract`: rural ward seats in the 2011 sheets vs the commission's category-wise abstract | external | **pass** | {"parsed": 6471, "published": 6471} |
| `2011_vp_ward_seats_vs_abstract`: rural ward seats in the 2011 sheets vs the commission's category-wise abstract | external | **warn** | {"parsed": 99322, "published": 99324} |
| `2011_vp_ward_winners_by_community_sex_vs_abstract`: village ward winners by community and sex vs the abstract | external | **warn** | {"total_abs_gap": 2} |
| `2011_ward_one_winner`: every candidate-table ward has exactly one elected candidate | internal | **pass** | {"wards_with_candidates": 7126, "not_one": 0} |
| `2011_ward_candidate_keys`: candidate serial numbers are unique within each source ward | internal | **pass** | {"duplicates": 0} |
| `2011_ward_union_present`: village and union wards retain their printed union identifier | internal | **pass** | {"missing": 0} |
| `2011_ward_printed_keys`: repeated printed ward identifiers are retained for source review and every row of one is marked gp_name_repeated | internal | **warn** | {"duplicates": 26, "unmarked": 0} |
| `2019_ward_one_winner`: every candidate-table ward has exactly one elected candidate | internal | **pass** | {"wards_with_candidates": 82298, "not_one": 0} |
| `2019_ward_candidate_keys`: candidate serial numbers are unique within each source ward | internal | **pass** | {"duplicates": 0} |
| `2019_ward_union_present`: village and union wards retain their printed union identifier | internal | **pass** | {"missing": 0} |
| `2019_ward_printed_keys`: repeated printed ward identifiers are retained for source review and every row of one is marked gp_name_repeated | internal | **pass** | {"duplicates": 0, "unmarked": 0} |
| `2021_ward_one_winner`: every candidate-table ward has exactly one elected candidate | internal | **pass** | {"wards_with_candidates": 24758, "not_one": 0} |
| `2021_ward_candidate_keys`: candidate serial numbers are unique within each source ward | internal | **pass** | {"duplicates": 0} |
| `2021_ward_union_present`: village and union wards retain their printed union identifier | internal | **pass** | {"missing": 0} |
| `2021_ward_printed_keys`: repeated printed ward identifiers are retained for source review and every row of one is marked gp_name_repeated | internal | **pass** | {"duplicates": 0, "unmarked": 0} |
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

`make links` writes `data/linkage/vp_2011_2019.parquet` and
`data/linkage/vp_2011_2021.parquet`: a 2011 president seat paired with its
2019 or 2021 seat. **9,491 links to 2019 and 2,747
to 2021** (11,972 with names identical after folding,
266 fuzzy). A link says two panchayat names agree inside
matching unions; it is not an official identifier or proof of unchanged
boundaries.

The use is a comparison of seats open in 2019/2021 by whether they were
women's seats in 2011. A wrong link adds noise and can bias it; a missing link
only costs sample. Doubtful pairs are left unlinked.

**Keys.** Each side carries the key the results tables identify a row by,
`district_code`, `block`, `gram_panchayat`, suffixed `_2011` and `_2019` /
`_2021`. That triple is unique in every results table (checked, including the
2021 by-elections; 2021 links point only at ordinary-election rows), and no
seat is linked twice. Also: `source_page_*`, `name_folded_*`, `union_group`
and the crosswalk decisions behind it, `qualifiers`, `folded_ratio`,
`skeleton_ratio`, `name_score`, `link_rule` (`exact_folded_name` /
`fuzzy_name`) and `candidate_name_shared` (the check below; not a match
feature).

### Union crosswalk

`data/linkage/union_crosswalk_2011_2019_2021.csv`, coded by hand from
`make union-evidence`: for each 2011 union, how many of its panchayats have
their best name match in each later union of the same district or of the
districts carved from it. An edge needs at least 3 identical folded names and
15% of either union; the shared names of every edge that was not one-to-one
were read. All 385 unions of 2011 and 388 later unions are covered.

| Decision | Rows | Where |
|---|---:|---|
| same | 368 | including spelling-only name differences (தொட்டியாம் / தொட்டியம், டி கல்லுபட்டி / தே.கல்லுப்பட்டி) and unions now in a new district |
| split | 27 | Cuddalore: கம்மாபுரம், காட்டுமன்னார்கோயில், கீரப்பாளையம் each gave panchayats to the new ஸ்ரீமுஷ்ணம். Dharmapuri: பென்னகரம் → ஏரியூர்; மொரப்பூர் → கடத்தூர். Tirunelveli/Tenkasi: குருவிகுளம், பாப்பாகுடி, மானூர், மேலநீலதநல்லூர் exchanged panchayats. Vellore/Ranipet/Tirupathur: காவேரிப்பாக்கம் went to three Ranipet unions; சோளிங்கர் partly to காட்பாடி; பேரனாம்பேட்டை to பேர்ணாம்பட்டு and மாதனூர்; மாதனூர் partly to அணைக்கட்டு |
| merged | 4 | the receiving sides of those moves (tnv ஆலங்குளம் → tki ஆலங்குளம்; vlr அணைக்கட்டு, அரக்கோணம், காட்பாடி) |
| uncertain | 1 | vlr திமிரி → வேலூர்: three generic names (குப்பம், புதூர், வெங்கடாபுரம்) while திமிரி keeps 55 of 55; not used |

No union was renamed. Linked unions are closed into groups, so a split forms
one blocking group.

### Matching

preclink 1.2.0: `block(on=union_key, crosswalk=...)`,
one name comparison, `filter(min_score=0.94-0.05, margin=0.05)`, `decide("hungarian")`,
run in both directions; a link must be found both ways and score at least
0.94.

- **Folding.** The commission's ா-for-ர keying (மாாியம்மன்), long and short
  vowels, ண/ன/ந, ள/ழ/ல, ற/ர, ஷ/ஸ/ஜ/ச, a nasal before a consonant typed as
  any nasal, doubled consonants at a join, a leading இ before ர or ல, a
  second vowel sign left by decoding, spaces and punctuation.
- **Score.** The largest of the folded ratio, the ratio with ா and the pulli
  dropped less 5 points, and the ratio with every vowel sign dropped less 12
  points. The last cannot carry a link by itself (it would make கோட்டமங்கலம்
  and குடிமங்கலம் one name) but counts as a rival in the margin.
- **Qualifiers must agree**, and one stated on only one side vetoes: numbers
  (25 வேப்பம்பட்டு, எண்.2, I சேத்தி), lettered parts (ஏ/சி), dotted initials
  by consonant (எஸ். ≠ எம்.; K. = கே.), directions (கிழக்கு, மேற்கு, வடக்கு,
  தெற்கு, fused or in brackets, and வட / தென் starting a word), மேல / கீழ /
  நடு, சின்ன / சிறு / பெரிய, புது / பழைய. A name that is a short prefix of
  the other is vetoed.
- **Threshold 0.94**, from the review: the 0.90–0.94 band came to 96%
  and 0.85–0.90 to 85%.
- **block_seq has weight 0.** It is file order, not a printed number, and it
  is not stable: among exact-name links in unchanged unions only 11.7% keep
  their rank within the union (median rank correlation 0.52).
- **Not used:** reservation, winner sex, winner or candidate names.
- **Excluded:** 16 (2011) and 14 (later) seats whose
  folded name and qualifiers repeat inside a union group.

### Coverage

| 2011 district | Later districts | Year | 2011 seats | Later seats | Linked |
|---|---|---:|---:|---:|---:|
| Ariyalur | ari | 2019 | 200 | 201 | 200 |
| Coimbatore | cbe | 2019 | 228 | 228 | 226 |
| Cuddalore | cud | 2019 | 683 | 683 | 676 |
| Dindigul | dgl | 2019 | 306 | 306 | 301 |
| Dharmapuri | dpi | 2019 | 251 | 251 | 239 |
| Erode | erd | 2019 | 225 | 225 | 221 |
| Karur | kar | 2019 | 157 | 157 | 155 |
| Krishnagiri | kgi | 2019 | 333 | 333 | 329 |
| Kanniyakumari | kkm | 2019 | 95 | 95 | 95 |
| Kancheepuram | kpm, cpt | 2021 | 633 | 632 | 630 |
| Madurai | mdu | 2019 | 420 | 420 | 418 |
| Nagapattinam | ngp | 2019 | 434 | 434 | 432 |
| Nilgiris | nlg | 2019 | 35 | 35 | 35 |
| Namakkal | nmk | 2019 | 322 | 322 | 316 |
| Pudukkottai | pdk | 2019 | 497 | 497 | 486 |
| Perambalur | pmb | 2019 | 121 | 121 | 121 |
| Ramanathapuram | rmd | 2019 | 429 | 429 | 429 |
| Salem | slm | 2019 | 385 | 385 | 382 |
| Sivaganga | svg | 2019 | 445 | 445 | 442 |
| Theni | thn | 2019 | 130 | 130 | 130 |
| Tiruvallur | tlr | 2019 | 526 | 526 | 515 |
| Thanjavur | tnj | 2019 | 589 | 589 | 565 |
| Tirunelveli | tnv, tki | 2021 | 425 | 425 | 401 |
| Tiruppur | tpr | 2019 | 265 | 265 | 263 |
| Tiruchirappalli | try | 2019 | 404 | 404 | 395 |
| Thoothukudi | tut | 2019 | 403 | 403 | 401 |
| Tiruvannamalai | tvm | 2019 | 860 | 860 | 856 |
| Tiruvarur | tvr | 2019 | 430 | 430 | 421 |
| Vellore | vlr, tpt, rpt | 2021 | 743 | 743 | 655 |
| Virudhunagar | vnr | 2019 | 450 | 450 | 442 |
| Villupuram | vpm, kki | 2021 | 1,099 | 1,100 | 1,061 |
| **All** | | | **12,523** | **12,524** | **12,238** |

Vellore is lowest (88%): its 2011 file was keyed loosely and its unions were
reorganised across three new districts.

### Precision (hand review)

`data/linkage/review_2011_2019_2021.csv`. Every fuzzy link was read; exact
links by random sample. A pair was judged from both names, the best rival
name on each side, and the union. `unsure` counts as wrong. The reviewer is
Claude, not a person.

| Stratum | Links | Reviewed | Correct | Precision | 95% CI (Wilson) |
|---|---:|---:|---:|---:|---|
| exact (identical as printed) | 11,604 | 76 | 76 | 100.0% | 95.2–100.0% |
| exact after folding, spelled differently | 368 | 45 | 45 | 100.0% | 92.1–100.0% |
| fuzzy 0.94–0.97 | 259 | 259 | 256 | 98.8% | 96.7–99.6% |
| fuzzy 0.97–1.00 | 7 | 7 | 7 | 100.0% | 64.6–100.0% |

Stratified estimate 99.98%; the lower bound (Wilson lower limits weighted by
stratum size) is 95.1%, set almost entirely by the 76-link sample
of exact links. The three unsure fuzzy links: கல்லான்குப்பம் / கல்லாலங்குப்பம்,
கரும்பத்தூர் / கருகம்பத்தூர், வெத்தலைக்காடு / வத்தலைக்காடு.

Below the threshold: of 69 pairs at 0.90–0.94, 66 are the same place;
of 74 at 0.85–0.90, 63 (one clearly different: ரெங்கநாதபுரம் /
ரெகுநாதபுரம்). Lowering the threshold to 0.90 would add about 66 correct and
3 doubtful links. Of 30 pairs scoring at least 0.80 that the margin or the
two-way rule dropped, 29 were different villages and 1 a lost link.

What the review changed: the first version scored the consonant skeleton less
5 points, which let vowel-quality differences through (தாடையூர் / தொடையூர்)
and scored கோட்டமங்கலம் / குடிமங்கலம் at 0.95; and it missed வட as a
direction (கடப்பந்தாங்கல் / வடகடப்பந்தாங்கல்).

### Independent check

`linkage/candidate_check.py` shares no code with the name match: does any
candidate for president in 2011 have the same name (normalised separately) as
any candidate for the linked seat later?

| Pairs | Share with a candidate name in common |
|---|---:|
| all links | 10.8% |
| exact links (11,972) | 10.9% |
| fuzzy links (266) | 8.6% |
| random pairs in the same union group (50 permutations) | 0.12% |

Links share candidates about 90 times as often as random pairs. Fuzzy links
share less than exact links. Matched to the same 2011 unions, exact links
share 10.2% against 8.7%, a difference of −1.6 points (95% bootstrap
−4.8 to +2.0). This check cannot certify the fuzzy stratum: taken at face
value the gap allows about 15% of fuzzy links to be wrong, with wide
uncertainty. The precision claim for fuzzy links rests on the full hand
review.

### What a link does not settle

- **Two-term gap.** 2011 to 2019 spans two terms, because the 2016 election
  was cancelled.
- **Quota levels differ.** In 2006 and 2011 one third of president offices
  were reserved for women (2011: 4,291 of 12,524). The Tamil Nadu Panchayats
  (Amendment) Act, 2016 (L.A. Bill 5 of 2016; section 57 for president
  offices) raised it to half, so 2019 and 2021 reserve 50%.
- **Rotation.** TNRD notes that reserved president offices were rotated after
  ten years for 2006 (G.O.Ms.105/2006). Whether 2011 kept the 2006 roster can
  be checked from Gazettes 228 and 318, but has not been checked.

## Reproduce

```
make sync
make collect      # network; tnsec.tn.gov.in needs TN_PROXY
make data         # parse data/raw into data/<year>/; rewrite the manifest
make links        # 2011 -> 2019/2021 links
make check
```
