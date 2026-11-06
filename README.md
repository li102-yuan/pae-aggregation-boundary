# Artifacts — The feasible region of cross-call aggregation exfiltration on LLM agents

Reproduction package: grid data, frozen pre-registrations, figure/table generators, and a
claim-to-data map. Start at **[`REPRODUCE.md`](REPRODUCE.md)** — it maps every table and
figure to the CSV it comes from and the one command that regenerates it.

No model calls, no network, no proprietary data. The public workload is derived from the
tau2-bench release (MIT, commit `19f13ea`); secrets are synthetic.

## Contents
- `paper/` — manuscript source (`main.md`, `main.tex`, `refs.bib`), figures (SVG+PDF), tables (LaTeX)
- `analysis/` — result tables and `fig_w72.py` (regenerates all figures and tables)
- `configs/` — frozen specifications with `FREEZE_*.sha256`
- `src/spike/` — the deterministic replay, matcher, and counter implementations

## License
Code and data are released under the MIT License; see [`LICENSE`](LICENSE).
