# Artifacts -- The feasible region of cross-call aggregation exfiltration on LLM agents

Reproduction package: grid data, frozen pre-registrations, figure/table generators, and a
claim-to-data map. Start at **[`REPRODUCE.md`](REPRODUCE.md)** -- it maps every table and
figure to the CSV it comes from and the one command that regenerates it.

No model calls, no network, no proprietary data. The public workload is derived from the
tau2-bench release (MIT, commit `19f13ea`); all secrets are synthetic.

## Contents

- `paper/` -- manuscript source (`main.tex`, `refs.bib`), figures (SVG + PDF), tables (LaTeX),
  the submission metadata and the highlights file
- `analysis/` -- result tables, the analytic-crossing record, the aggregate statistics of the
  construction matrix (`tau_pair_matrix_summary.md`), and `fig_w72.py`, which regenerates every
  figure and table in one run
- `configs/` -- frozen specifications with `FREEZE_*.sha256`
- `src/spike/` -- the deterministic replay, matcher and counter implementations
- `requirements.txt` -- pinned Python dependencies for the figure/table generator

## Quick check

```bash
python -m pip install -r requirements.txt
python analysis/fig_w72.py
sha256sum -c configs/w11spike/FREEZE_W11SPIKE.sha256   # run from configs/w11spike/
```

The second command rebuilds all nine artefacts and prints `FIG_TEXT_GATE=PASS` plus a
font/geometry check for each figure; the third verifies the frozen inputs.

## License

Code and data are released under the MIT License; see [`LICENSE`](LICENSE). The airline
workload keeps its own upstream license at `configs/w11airline/data/LICENSE`.
