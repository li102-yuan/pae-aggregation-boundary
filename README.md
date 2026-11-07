# Reproduction artefacts — cross-call aggregation exfiltration on LLM agents

This repository contains the **data, frozen specifications, and code** needed to regenerate
every table and figure of the associated manuscript. The **public repository** does not
contain the manuscript text (the article is submitted to the *Journal of Network and Computer
Applications* and no preprint
is posted); the supplementary archive submitted with the article does include the LaTeX source
(`paper/main.tex`) so the tables and figures can be regenerated in context.
Start at **[`REPRODUCE.md`](REPRODUCE.md)** — it maps each figure/table to its input CSV and the
single command that regenerates it.

No model calls, no network, no proprietary data. The benign workload is derived from the public
tau2-bench release (MIT); all secrets are synthetic.

## Contents
- `analysis/` — result tables, the generator `fig_w72.py`, and the geometry checks
- `configs/` — frozen pre-registrations with `FREEZE_*.sha256`
- `src/spike/` — deterministic replay, matchers, and the counter suite
- `paper/figures/`, `paper/tables/` — generated vector figures and LaTeX tables

## Notes on the source

Internal labels such as `W11.SPIKE`, `W7.3`, `D-0xx`, and `FIX-n` are window and decision
identifiers from the project's pre-registration log, retained for traceability. Some string
values (data-source descriptions, assertion messages, and decision notes) remain in Chinese,
the authors' working language; they are part of the frozen inputs and do not affect any output.

## License
MIT; see [`LICENSE`](LICENSE).
