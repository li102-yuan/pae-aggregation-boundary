# C&S submission metadata (highlights, declarations, AI disclosure)

The manuscript carries every declaration in its own Declarations block; this file is the
copy-paste source for the submission system and must stay word-for-word consistent with it.

## Highlights
The five highlights are delivered as a separate file, `paper/highlights.txt` (plain text,
one per line, all <= 85 characters including spaces).

## CRediT author statement
Peiyuan Li: Conceptualization, Methodology, Software, Formal analysis, Investigation,
Data curation, Writing – original draft, Visualization, Validation, Supervision,
Writing – review & editing.

## Declaration of competing interest
The author declares no known competing financial interests or personal relationships that
could have appeared to influence the work reported in this paper.

## Funding
This research received no external funding.

## Ethics
Not applicable: no human subjects, no personal data, no animal experimentation.
The workloads are public benchmark tasks and the secrets are synthetic.

## Data availability
All artifacts needed to reproduce every table and figure are provided as supplementary material
with this submission: the frozen configuration files, the deterministic replay and counter code
(`src/spike/**`), the aggregated per-table result files (`analysis/*.csv`), the figure and table
generators, and a claim-to-data map (`REPRODUCE.md`). Full per-call logs are retained by the
authors and are available from the corresponding author on reasonable request.

The supplementary archive is `paper_w72_submission.zip` (rebuilt from the reproduction
package: `REPRODUCE.md`, `analysis/*.csv`, `src/spike/**`, `configs/**`, `paper/**`, MIT
LICENSE). No proprietary or personal data were used. The public workload is derived from the
tau2-bench release (MIT, commit 19f13ea); all secrets are synthetic.

## Declaration of generative AI and AI-assisted technologies
During the preparation of this work the author used an AI assistant for language
editing and for drafting figure-generation scripts. The author reviewed and edited
the content and takes full responsibility for the content of the publication.
