# Aggregate statistics of the tau-pair construction (main matrix)

This file collects the **aggregate** readings of the construction-internal matrix behind
Theorem 1 and Section 3 of the manuscript. The per-pair raw records and the full per-call logs
are retained in the authors' private archive and are available from the corresponding author on
reasonable request; they are not shipped with the supplementary archive. All headline numbers in
the paper can be checked against the aggregates below without those raw records.

## Two populations, not one subtraction chain

| Quantity | Value | Source experiment |
|---|---|---|
| tau pairs constructed | 126 pairs / 252 episodes / 1352 fragments | construction set, 20 intents |
| judgment set (single-field scope) | 104 pairs | construction re-audit, "G1" |
| excluded at that re-audit | 22 pairs (17.5% of 126) | construction re-audit |
| grid judged pairs | 92 = 72 (F1) + 20 (F7) | later coverage-sweep construction |

The 104-pair set and the 92-pair set are **different populations**, used by different
experiments; 104 - 92 is not a meaningful residual. The second-field family executed 22 pairs,
of which 2 were development pairs and 20 were judged, so 72 + 20 = 92.

The 28 six-byte fragments quoted in the manuscript (Section 6) are 14 pairs times two halves:
9 F1 judged pairs, 4 F7 judged pairs, and **one** of the two F7 development pairs. The second
F7 development pair has a different fragment length and is not part of that count, so the
"2 development pairs" and "28 fragments" statements are consistent rather than contradictory.

## Identity and construction-internal readings (104-pair set, unless noted)

| Reading | Value | Note |
|---|---|---|
| A1 / A1' / A2' / A3 / A3' / A3'' / A4 identity checks | 126/126 each | over all 126 constructed pairs |
| harm-point identity (first reconstruction index = first deny index) | 104/104 | judgment set |
| benign-arm full release | 104/104 | judgment set |
| outbound content byte-identical between arms | 572/572 calls | judgment set |
| utility under the Oracle criterion | 104/104 = 1.00 | judgment set |
| complete-reconstruction rate | 0/104 | Wilson 95% upper bound 3.56% |
| pre-registered risk threshold | 5% | the "delta_gate" of the manuscript |

## Coverage-sweep readings (92-pair set)

| Reading | Value |
|---|---|
| F1 structural interception (all/judged) | 72/72 |
| F7 structural interception (all/judged) | 20/20 |
| matchable denominators with M2 and unmatched = allow | 63/72 = 87.5%, 16/20 = 80.0% |
| ceiling with the shorter matcher | 72/72, 20/20 |

The grid CSV files shipped in `analysis/` reproduce every table and figure of the paper. This
file exists because the 104-pair matrix itself is not re-run by `analysis/fig_w72.py`; it records
the aggregates so the two populations cannot be confused.
