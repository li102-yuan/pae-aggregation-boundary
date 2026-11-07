# Reproduction artefacts — cross-call aggregation exfiltration on LLM agents

This repository contains the **data, frozen specifications, and code** needed to regenerate
every table and figure of the associated manuscript. It intentionally does **not** contain the
manuscript text: the article is submitted to *Computers & Security*, and no preprint is posted.
Start at **[`REPRODUCE.md`](REPRODUCE.md)** — it maps each figure/table to its input CSV and the
single command that regenerates it.

No model calls, no network, no proprietary data. The benign workload is derived from the public
tau2-bench release (MIT); all secrets are synthetic.

## Contents
- `analysis/` — result tables, the generator `fig_w72.py`, and the geometry checks
- `configs/` — frozen pre-registrations with `FREEZE_*.sha256`
- `src/spike/` — deterministic replay, matchers, and the counter suite
- `paper/figures/`, `paper/tables/` — generated vector figures and LaTeX tables

## License
MIT; see [`LICENSE`](LICENSE).
