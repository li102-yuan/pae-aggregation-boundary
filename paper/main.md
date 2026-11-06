<!-- =====================================================================
  W7.2 正文母本（单一源；附加纪律 C1：md 母本 → tex 生成，改完跑"摘要逐字一致 + 未改行字节一致"）
  进度 = 第 1–5 段：标题＋摘要＋贡献＋关键词＋§1–§11 全部成稿。
  待办见文末定稿注释（\ref 替换、REPRODUCE、文献核验、闸门抽查）。

  图/表键与首现（附加纪律 B1–B3；图号首现顺序由脚本扫 "Figure N" 复查，现序 1<2<3 单调）：
    Figure 1 = paper/figures/fig1_frontier   （§1 首现，§4 复引）
    Figure~\ref{fig:geometry} = paper/figures/fig2_geometry   （§5 首现）
    Figure~\ref{fig:lmin} = paper/figures/fig3_lmin       （§6 首现）
    Table 1a/1b = paper/tables/tab1a_main.tex / tab1b_cost.tex（§4 首引，§8 复引）
    Table 2  = paper/tables/tab2_counters.tex（§7 首引）

  交叉引用（定稿检查段 2026-11-05 已机械替换）：§1–§3 的两处陈旧前向节号已改为
  §\ref{sec:c1}／§\ref{sec:trap}；全篇本文节号一律 §\ref{sec:*} 键，节标题带 pandoc
  label {#sec:*}；图/表引用为 Figure~\ref{fig:*}／Table~\ref{tab:*}。报告中与 docx 的
  节号（如 w11spike_report §5.3、docx v2.2 §3）按原样保留，不是本文节号。

  术语（D-025 §五，全篇强制）：
    complete-reconstruction rate（原 risk）｜partial-leakage fraction H（原 H）｜
    structural interception rate（原 拦截率）｜nominal remaining uncertainty under the
    uniform-independent-hex assumption（原 残熵）；24 bit 是运行判据，非安全强度。

  禁词扫描口径（附加纪律 C5 + D-021/D-025 禁词表；清单本体见 DECISIONS.md，本文件不复述，
  以免扫描自命中）：除两条白名单外全文 0 命中——
    (i) "complete" 仅出现于强制术语 complete-reconstruction rate（D-025 §五-2）；
    (ii) "first" 仅出现于既有事件名 first deny / first reconstruction point。
    二者均为术语而非主张词；"first deny" 属机制事实陈述，非新颖性主张。

  三读数口径注：§2–§3 的 τ 对构造内读数无逐 episode H/残熵（W2.4/W6.2 未记录该量），
  故以 (判别, complete-reconstruction rate, utility) 三元组并列披露；coverage 网格的
  (structural interception rate, partial-leakage fraction, 标称剩余不确定性) 三读数
  自 §4 起逐表并列（Table 1a/1b，§7 起 Table 2）。自检脚本：reports/audit/w7.2_prose_check.py。

  文献（W0.7 已收口，原占位键 key-aggregation/key-dlp/key-camel 已废止）：全文 38 条，
  键名 姓+年+短词，逐条经 Crossref（DOI）或 arXiv API 现场核验，落点与 HTTP 状态见
  reports/audit/w0.7_refcheck.md；bib 对齐复查 reports/audit/w0.7_bibcheck.py，
  md↔tex 引用集合比对 reports/audit/w0.7_citecheck.py。
===================================================================== -->

# The Feasible Region of Cross-Call Aggregate Exfiltration in LLM Agents

*Why Coverage-Closure Criteria Buy Neither Low Benign Misfire nor High Residual Uncertainty*

<!-- 负责人定稿标题（中文原案，2026-11-05）：《LLM Agent 跨调用聚合外传的可行域：覆盖闭包类防御为何买不到低误拦与高残熵》。
     英文渲染规避防御性称谓与绝对化词（硬要求 2 与标题纪律）；副标题 "residual uncertainty"
     是正文 "nominal remaining uncertainty"（24 bit 为运行判据）的标题简写。
     闸门 6 口径：可行域为空在正文以 H1–H4 条件陈述（§4），标题不断言无条件不可能。 -->

**Abstract** (word count: 179 tokens; assumed hard cap 200 words, ≥5-word headroom — see [^abstract-map])

The exfiltration we care about is aggregation-based: the agent moves a secret out fragment by
fragment, where every individual call is legitimate. The result is an empty feasible region under H1–H4: ⑤ forces θ′ ≤ 7/12; ① forces θ′ ≥ θ* > 7/12; no θ′ satisfies both. Under H3 the
post-interception nominal remaining uncertainty is R = 4·(L − delivered) ≥ 4L(1−θ′) + 4 − 4δ
(δ the ceiling remainder), safely R ≥ 4L(1−θ′); at θ′ = 1.0 this gives R = 4 bit with
H = 0.975. The correct statement is therefore conditional on the workload: the empty region
is write-granularity-independent and determined by the per-task final-coverage distribution.
The 234-combination scan (102 combinations in the candidate pool) instantiates the
proposition and is not part of its proof: under the union and unique ambiguity readings the
scan yields 0/102 combinations passing all five gates (Wilson 95% upper bound 3.6%). On the
second workload the picture is direction-consistent but power-limited: airline field-level
write tasks, n = 15 — quantitatively this paper is anchored to retail, and no
workload-independence is claimed.

**Contributions.**

- **C1 — Conditional empty feasible region (§\ref{sec:c1}).** Under four explicitly checkable
  assumptions H1–H4, no threshold θ′ of the single-field coverage-closure family satisfies
  the benign-cost gate (①) and the post-interception uncertainty gate (⑤) together; the
  234-combination scan (102 combinations in the candidate pool) yields 0/102 passing all
  five gates under both ambiguity readings.
- **C2 — Attribution-blind criteria cannot discriminate (§\ref{sec:tau}).** Theorem 1: a deterministic
  criterion whose state depends on the traces only after attribution is erased returns
  identical per-call decisions on both arms of any τ pair, at any threshold — measured on
  104 constructed pairs (outbound content byte-identical on 572/572 calls; discrimination
  rate 0), with the attribution-sensitive `K_B` as the boundary witness (104/104 intercept,
  no benign-arm denial).
- **C3 — ℓ_min and the three-reading protocol (§\ref{sec:lmin}–§\ref{sec:trap}).** The minimum attributable fragment
  length (8 bytes; 28 six-byte fragments structurally unmatchable) caps allow-arm
  interception at 63/72 and 16/20 (matchable over all judged pairs), and every structural
  interception reading is reported only alongside the partial-leakage fraction H and the
  nominal remaining uncertainty R — at θ′ = 1.0: 1.00 with H 0.975 and 4 bit.

**Keywords:** LLM agent; tool calling; data exfiltration; aggregation; coverage closure;
measurement


## 1. Threat and problem statement {#sec:threat}

The workload we study is the standard tool-using agent setting of τ²-bench-style database
agents \cite{barres2025tau2,yao2024taubench} — one point in a line of tool-use benchmarks that
runs from API-catalogue agents \cite{qin2023toolllm} to multi-environment suites
\cite{liu2023agentbench} (docx v2.2 §3; scenario fixes in D-002): an agent operates on a
relational backend through whitelisted tools exposed over the Model Context Protocol
\cite{mcp2025spec}, and secrets — credentials, tokens, recovery codes — live inside
registered fields. The exfiltration we care about is **aggregation-based**: the agent moves a
secret out **fragment by fragment**, where every individual call is legitimate. Each call
carries a declared cell, offset, length, channel and encoding; each passes per-call
authorization on its own. No single call is a violation; the violation is the **assembly** of
the fragments on an external sink. Per-call inspection is therefore structurally blind to the
threat, and the remedy must be **state across calls**.

That remedy immediately raises the question this paper measures: *what kind of cross-call
state buys what, and at what price?* Three quantities have to be reported together for any
answer to be meaningful: a discrimination reading (can the criterion tell the two arms of a
τ pair apart), a cost reading on benign traffic, and a leakage reading after interception
(structural interception rate, partial-leakage fraction `H`, and nominal remaining
uncertainty under the uniform-independent-hex assumption). Reporting interception alone
turns "one byte short of full delivery" into "intercepted"; we return to this trap in §8.
Figure~\ref{fig:frontier} previews the measured outcome for the single-field coverage family: the benign-misfire
side and the post-interception uncertainty side of the trade-off never hold at the same
candidate threshold; §\ref{sec:c1} states the conditional proposition behind it and its assumptions.

## 2. Attribution-blind criteria cannot discriminate a τ pair {#sec:tau}

**Construction.** A **τ pair** is a benign trace `b` and a dangerous trace `m` of the same
length `n ≥ 2` such that (τ1) for every call `i < n`, the two calls are equal after
**erasing attribution** — same byte lengths, channels, encodings and contents, differing only
in which cell each fragment is attributed to; (τ2) the last call is fully identical, including
attribution; (τ3) `m`'s fragments all land in **one** cell while `b`'s fragments land in
**distinct** cells. The construction realizes exactly this: the dangerous arm slices one
secret into consecutive fragments of one field; the benign arm writes the same byte volume
spread across `k` distinct registered fields, one fragment per field, per-call depth `1/k`.
We constructed 126 τ pairs across 20 intents; 104 pairs form the judgment set.[^tau-src]

**Theorem 1 (attribution-blind ⇒ no discrimination; any threshold).** Let a deterministic
defender be an order-insensitive accumulator (commutative, associative per-fragment updates,
decision taken before commit) whose inputs depend on the traces only **after attribution is
erased**. Then on any τ pair the two arms receive **identical per-call decisions** — identical
allow/deny sequences and identical first-deny call index — for *every* threshold θ′.
The discrimination rate on τ pairs is 0 for this entire class. No resource assumption is
involved: enlarging the state, lengthening the history window or adding a content memo does
not move the conclusion, because the missing ingredient is an **invariant** (state must
survive erasure), not capacity.[^thm-src]

Two measured fingerprints pin the theorem to the constructed traces. (a) On the byte side,
the two arms are indistinguishable call by call: outbound content is byte-identical on
**572/572** calls, and decision-point content hashes coincide on **104/104** pairs — so any
criterion reading only the byte stream sees one trace, not two. (b) On the state side, the
boundary of the theorem is
**attribution**, not representation: the per-cell interval-union criterion `K_B` is also an
order-insensitive accumulator, but its state is cell-indexed, so it sits outside the class —
and it does discriminate, denying the dangerous arm on **104/104** pairs while never denying
the benign arm on any of them.[^kb-boundary] A controlled triple in the grid makes the same point by
changing one variable: with lineage, matcher, denominator and θ′ fixed and only the **scope**
widened (per-cell → per-entity → whole-session), discrimination on the second-field family
`F7` collapses **20/20 → 0/20 → 0/20** while per-cell misfire is unchanged at 39/68 until the
whole-session row trades it down to 15/68 *by* losing `F7`. Attribution granularity is the
carrier of discrimination; coarsening it buys lower misfire only by surrendering the
discrimination.[^scope-triple]

Two caveats keep this section honest. (i) A minimal witness `R★` — deny as soon as any cell
has accumulated two fragments — discriminates every τ pair within at most two calls, but on
real benign traffic, where fragmented writes to the same field are the norm, it denies
essentially everything: it proves discrimination is *attainable*, not that it is *usable*.
(ii) Our `F1`/`F7` counts (denominators 72/20 constructed pairs) and our misfire counts
(denominator 68 holdout tasks) come from **different populations**; for attribution-blind
criteria their conjunction is vacuous, so wherever both appear we label the populations
explicitly. The complementary half of the story — attribution is **not sufficient**: once a
criterion does track per-cell attribution and account by capacity, the coverage family still
cannot buy low benign cost and high post-interception uncertainty together — is stated
conditionally in §\ref{sec:c1}; the two halves are one result and are cited only as a pair.

## 3. The within-construction lens: `K_B` closes inside its definition domain — and costs 55.9% outside it {#sec:lens}

`K_B` keeps, per cell, the union of delivered intervals and denies when
`cov(k)/field_len(k)` reaches the threshold. Under the deployed threshold θ = 0.55 (frozen
policy), on the 104 constructed τ pairs it denies the dangerous arm **104/104** times, with
the first deny landing **1–3 calls before** the call carrying the secret-completing
fragment, and it
never denies the benign arm on any of the 104 pairs; utility is **104/104 = 1.00** under the
pre-registered Oracle criterion (each benign episode delivers all of its per-channel
artifacts).[^kb-consts]
The utility reading is a **within-construction** statement — the benign arm's write depth is
below θ *by construction* (depth `1/k` per cell), so 1.00 certifies that the criterion closes
inside its definition domain, not that it is harmless on real traffic.

The leakage-side and the cost-side readings are therefore stated in one paragraph, as the
within-construction lens requires. On the leakage side, the dangerous arm's
**complete-reconstruction rate** is **0/104** (Wilson interval
\cite{wilson1927probable,brown2001interval}, 95% upper bound 3.56%, within the
pre-registered δ = 5%).[^g2-src] On the cost side, the paired number is the real-workload
reading: on the 68-task holdout of the retail domain, `K_B`'s lineage-free baseline denies
**38/68 = 55.9%** of benign tasks (Wilson 95% interval 44.1–67.1); for this baseline row the
union and unique ambiguity readings coincide (no ambiguous benign fragments).[^misfire-src]
The two populations must not be merged: 104 τ pairs and 68 holdout tasks are different
populations (§\ref{sec:tau}, caveat ii), and the within-construction triple (intercept 104/104,
complete-reconstruction 0/104, utility 1.00) and the real-workload misfire 38/68 are the two
halves of the within-construction lens that D-021 §四-2, as revised by D-025 §三-1, requires
us to report side by side. What §\ref{sec:lens} therefore claims for `K_B` is exactly this: **it closes
within its definition domain** — discrimination is attainable at deployment — and, on the
only real-workload measurement we have, it costs a majority of benign tasks. Whether that
cost can be traded down by candidate thresholds, and what the trade gives up on the leakage
side, is the subject of §5.

## 4. The coverage-closure family has an empty feasible region under H1–H4 (C1) {#sec:c1}

Fix the family to single-field coverage closure: a criterion `D = (S1, D1, lineage, matcher,
norm, unmatched, dest=off, θ′)` that denies when the per-cell delivered-interval union covers
a fraction θ′ of the field capacity. θ′ is a candidate grid parameter, not the deployed
θ = 0.55. Four explicitly checkable assumptions carry the result:

- **H1 (misfire-leg workload geometry).** Every θ′ meeting the benign-cost gate ① —
  benign misfire ≤ 30% — satisfies θ′ ≥ θ*, and θ* > 7/12. On the six-point grid, benign
  misfire measured on the same rows that carry the leakage readings (`C031`–`C036`; 68-task
  retail holdout; union reading) is 57.4 / 55.9 / 38.2 / 38.2 / 38.2 / 16.2% (unique reading
  55.9 / 51.5 / 33.8 / 33.8 / 33.8 / 16.2%), so the gate-①-feasible threshold is θ* = 1.00;
  the analytic crossing from the per-task final-coverage distribution is θ′ > 0.9877 (§\ref{sec:geometry}).
  The lineage-free probe rows (`C001`–`C006`) read 55.9 → 16.2% (union = unique) and are what
  Figure~\ref{fig:frontier}'s left axis plots.[^c1-src]
- **H2 (attribution reliability).** Delivered truth bytes are booked to the field carrying
  them. Construct-holds for the oracle arm; for content attribution the matcher guarantees it
  whenever the secret is unique — `ambiguous_malicious = 0` on 234/234 grid rows.
- **H3 (encoding and entropy).** Secret alphabet of 2^b characters, independent and uniform,
  b ≤ 4; all secrets are hex (b = 4).
- **H4 (family and accounting).** scope = S1, denominator = single-field capacity, dest = off
  (the weakest setting), criterion ⑤ aggregated per worst episode (min R, max H).

Two lemmas do the work. *Delivery cap:* an allowed call delivers at most
K(θ′, L) = ⌈θ′L⌉ − 1 truth bytes of the field, and — because every allow commits its
intervals — a whole episode delivers at most K(θ′, L) bytes **regardless of how many calls
the attacker spends**; the C-B** construction attains the bound at every grid point.
*Uncertainty floor:* under H3 the post-interception nominal remaining uncertainty is
R = 4·(L − delivered) ≥ 4L(1−θ′) + 4 − 4δ (δ the ceiling remainder), safely
R ≥ 4L(1−θ′); at θ′ = 1.0 this gives R = 4 bit with H = 0.975. *Threshold ceiling:* criterion
⑤ — R ≥ 24 bit and H ≤ 0.5 on every malicious episode, with R_min = 24 bit = 6 bytes — caps
the feasible θ′ at sup over L of θ₂(L) = 1/2 + 1/(2·6) = 7/12 ≈ 0.5833, attained at L = 12.

**Proposition (empty feasible region under H1–H4).** ⑤ forces θ′ ≤ 7/12; ① forces
θ′ ≥ θ* > 7/12; no θ′ satisfies both. On this workload the gap is θ* − 7/12 = 0.4167 (grid);
spending the ⑤ margin in full at the corner θ′ = 7/12, the analytic misfire reading is
36/68 = 52.9% (retail final-coverage ladder; an analytic reading, not a grid row) — still
22.9 pp above the 30% gate. Three consequences. The emptiness is not an artifact of the
24-bit operating criterion: any R_min ≥ 8 bit keeps the supremum ≤ 3/4 < 1. On this workload
the bound tightens to θ₂(40) = 21/40 = 0.525 < 0.55, so **every** grid point — including the
deployed 0.55 — violates ⑤; at θ′ = 0.55 the entropy leg passes (R_min = 24 bit) while the
H-leg fails (H_max = 0.5417). And for L ≥ 12 the H-leg dominates (H ≤ 0.5 implies
R ≥ 24 bit), so ⑤'s content is "deliver at most half". The 234-combination scan (102
combinations in the candidate pool) instantiates the proposition and is not part of its
proof: under the union and unique ambiguity readings the scan yields **0/102** combinations
passing all five gates (Wilson 95% upper bound 3.6%).[^nogo-src] By the multi-candidate
lemma the leakage leg is reading-invariant while the misfire leg is reading-dependent
(`C156` at θ′ = 1.0: 16.2% union vs 50.0% unique, both on the 68-task holdout), so the
emptiness holds under both readings, a fortiori under unique. Figure~\ref{fig:frontier} plots the two legs
across the six candidate thresholds; Table~\ref{tab:maina}/\ref{tab:mainb} report the candidate-family rows
(`C151`–`C156`, M2 with closed-world deny) with the union|unique misfire pair and the C-B**
leakage pair.[^c1-src]

Boundary. S2/S3 dilute the denominator and the proposition does not cover them: measured at
θ′ = 0.55, S3/D1 reaches 15/68 = 22.1% benign misfire (union; unique reading 34/68 = 50.0%;
Wilson 95% interval 13.8–33.3%) while its bound leg `F7` is 0/20 (Wilson 95% upper 16.1%; at
most 4/20 anywhere on the grid) — the wider scope buys the low misfire and the missing
interception as the same move. That is a conflict between ① and ②, not a counterexample to
the ①-vs-⑤ proposition (S2/D1 at 0.55 is 39/68 = 57.4%, union).

## 5. Write-granularity invariance: the region is governed by the final-coverage distribution {#sec:geometry}

The remaining degree of freedom behind H1 is benign write geometry. The W11.4 invariance
lemma closes it for this family and workload: under S1 with declared coordinates, re-chunking
a write trace (byte-conserving, consecutive slices, order-preserving) leaves every cell's
interval union unchanged, hence the per-episode deny decision unchanged, hence gate ①
unchanged. The sweep measures five write geometries G1–G5 — whole-field, halves, quarters,
eighths, ≤3-byte pieces; 318 input fragments re-chunked into 318 / 397 / 566 / 1014 / 10,476
pieces — and benign misfire on the 68-task holdout is identical point by point at all six
candidate thresholds: 38/68 (55.9%), 35/68 (51.5%), 23/68 (33.8%), 23/68 (33.8%), 23/68
(33.8%), 11/68 (16.2%); union and unique coincide (no ambiguous benign fragments). Figure~\ref{fig:geometry}
plots the five curves; they coincide exactly, with no jitter or offset. Chunking changes the
decision resolution — per-episode call volume grows from 199 to 6,489 across G1–G5 — not the
event rates.[^geom-src]

The correct statement is therefore conditional on the workload: **the empty region is
write-granularity-independent and determined by the per-task final-coverage distribution**.
Analytically, θ* = 0.9877 is the 21st largest per-task final coverage (0.987654): gate ①
requires θ′ > 0.9877, and between 0.8 and 0.9877 the misfire plateaus at 23/68 = 33.8%
(twelve tasks' final coverage lies in 0.979–0.989); the grid's gate-①-feasible point remains
θ′ = 1.00 (11/68 = 16.2%). On the second workload the picture is direction-consistent but
power-limited: airline field-level write tasks, n = 15, misfire 14/15 = 93.3% (no holdout;
Wilson 95% interval 70.2–98.8%), verdict UNDECIDABLE (D-026 §一) — quantitatively this paper
is anchored to retail, and no workload-independence is claimed.[^airline-src] H1 survives as
an assumption: what it constrains is the distribution of "how much of a field a legitimate
task writes", not the chunk size.

## 6. ℓ_min: the matchability boundary of M2, and the M2-short trade {#sec:lmin}

Content-fingerprint attribution (M2) indexes every ℓ-gram of a registered field by a keyed
content digest \cite{brin1995copy,krawczyk1997hmac} and matches a fragment against the index
rather than against plaintext \cite{charikar2002similarity,kornblum2006identifying}; it has a
minimum attributable fragment length
ℓ_min = 8 bytes. Thirteen judged pairs — 9 of `F1` (72 judged pairs) and 4 of `F7` (20 judged
pairs) — carry their secret as two 6-byte halves (12-hex-character secrets split in half);
with one `F7` development pair this is 28 fragments of 6 bytes, every one shorter than
ℓ_min. A fragment that cannot be attributed can never fire the coverage event, so on the
unmatched=allow arm the interception counts on these pairs are capped by arithmetic, not by
mechanism: the matchable denominators give F1 63/72 = 87.5% and F7 16/20 = 80.0% (matchable
over all judged pairs; M2, allow arm), and gate ② (≥ 90%) is arithmetically unreachable for
every allow row. Figure~\ref{fig:lmin} shows the two ceilings against the 90% gate; all denominators are
reported in dual form (all vs matchable) throughout.[^lmin-src]

M2-short lowers ℓ_min to 4 and the ceilings disappear (72/72, 20/20 on the same judged
pairs); what that buys on the match layer is paid back on the counter-packing layer (§\ref{sec:trap}).
ℓ_min is therefore stated as the M2 configuration's boundary plus the M2-short trade — not a
ceiling for the family. The two boundaries are orthogonal: matchability asks whether a
fragment can be seen at all; the coverage-layer proposition (§\ref{sec:c1}) says that seen, the fragment
still delivers at most half of what ⑤ tolerates.


## 7. The measurement trap: structural interception alone overstates the coverage family {#sec:trap}

The grid's interception flag is defined as `intercepted := delivered < truth_len`
(`gate.py` L191): a criterion that lets 11 of 12 secret bytes through in a single call — and
denies the twelfth — is recorded as intercepting. This is not a corner case but the
θ′-adaptive upper bound itself: the C-B** construction delivers
`h = ⌈θ′L⌉ − 1` bytes in one allowed call at **every** threshold, so the structural
interception rate is 1.00 (92/92 judged pairs per threshold, C031–C036) while the
partial-leakage fraction rises to H_max = 0.975 and the nominal remaining uncertainty falls
to 4 bit at θ′ = 1.0 — the right end of the frontier plot. A criterion can therefore sit at
"interception 1.00, H 0.975, 4 bit" and have surrendered essentially the whole secret.[^metric-src]

The reporting protocol used everywhere in this paper follows from the trap: a structural
interception rate appears only next to the partial-leakage fraction `H` and the nominal
remaining uncertainty `R` (Table~\ref{tab:maina}/\ref{tab:mainb} for the candidate family; Table~\ref{tab:counters} for the
counter-packing readings on the three closest candidates, where the C-B** column is exactly
this triple and the worst-case column adds the C-B* tail-delivery reading — `C204` delivers
12/12 bytes and is not intercepted at all). Two readings from Table~\ref{tab:counters} bear the point: `C156`
holds interception 1.00 with H 0.975 and 4 bit (denying one byte is not containment), and
`C204` holds interception 0.00 with H 1.000 and 0 bit (the L−1 head is delivered and the
1-byte tail falls back to its declared cell).

## 8. Closed-world denial is not structural coverage {#sec:cw}

The lowest benign-cost rows in the grid are the closed-world arm: `unmatched=deny` rejects
any fragment the matcher cannot attribute. Its reading depends on the ambiguity bookkeeping,
and the two readings must appear in one table: at θ′ = 1.0, `C156` denies 11/68 = 16.2% of
the holdout tasks under the union reading but 34/68 = 50.0% under the unique reading
(Table~\ref{tab:mainb}, row `C156`) — a factor of three produced by bookkeeping alone.[^cw-src]

The union reading's benign cost is low only because two construction facts hold
simultaneously. (i) **Benign writes are verbatim re-writes of library fields**: all 318
benign fragments match under both M1 and M2 with identical byte intervals (S-4 audit), so a
union-matching closed-world arm never rejects benign traffic — a property of this workload's
construction, not of content inference. (ii) **Multi-candidate hits count as coverage**:
under the unique reading the same 67 ambiguous benign fragments turn into unmatched events,
and 16.2% becomes 50.0%. Remove either fact and the closed-world arm's benign reading
degrades; neither fact is guaranteed by the criterion itself. The closed-world mechanism is
a deny policy layered on top of attribution, not an extension of structural coverage — and
§\ref{sec:cross-model} shows its "interception" readings do not survive the matchability boundary either.

## 9. Cross-model, in-loop, and across workloads {#sec:cross-model}

**Three models (N = 30 injection episodes per arm).** With the gate disabled and no
untrusted-content marking, injection-induced fragmented exfiltration succeeds on all three
servings \cite{greshake2023not,ferrag2025prompt,liu2023formalizing} — attack-success rate (the
injected secret fully delivered, the reading convention of the injection benchmarks
\cite{zhan2024injecagent,debenedetti2024agentdojo}) 30/30 = 1.00 on
`qwen3.8-max`, `deepseek-v4-pro` and `glm-4.6`, with H = 1.0 on every delivered episode. With
the coverage gate enabled (C2), the rate is 0/30 on all three (Wilson 95% upper bound 11.4%)
with H̄ = 0.492 / ≈0.5 / 0.500: the gate's within-construction readings replicate across
models. The encoded-injection arm breaks symmetry \cite{perez2022ignore}: 0/18 on `qwen` (Wilson
95% upper bound 17.6%) against 3/18 on `deepseek` (Wilson 95% interval 5.8–39.2%) and 3/18 on
`glm` — Base64
or hex payloads decoded and executed in one shot (H = 1.0), so the encoded threat re-enters
the threat model. The spread is not read as a capability ranking: the three servings are not
homogeneous (the main matrix ran `qwen` with thinking disabled; the reasoning-mode servings
handle thinking content differently), so the E1 arm is reported as a service-mode contrast,
and the cross-model limitation is stated as partial replication.[^xmodel-src]

**In the loop (N = 15 injection episodes per cell, one model serving).** Without the gate and
without marking, ASR is 15/15 = 1.00 with H = 1.0. Marking untrusted content (spotlighting,
\cite{hines2024spotlighting}) alone: ASR 0/15 (Wilson 95% upper bound 20.4%), H = 0. The gate
alone: ASR 0/15 (same upper
bound) with H̄ = 0.5 — completion is blocked while half the secret leaks, the measurement
trap of §\ref{sec:trap} in live traffic. Gate plus marking: ASR 0/15, H = 0. Benign utility under the
gate is unchanged in this construction (depth < θ by construction, §\ref{sec:lens}).[^inloop-src]

**Across workloads, the ℓ_min trade flips sign.** On retail, lowering ℓ_min from 8 (M2) to 4
(M2-short) removes the arithmetic ceilings of §\ref{sec:lmin} and **raises** the structural interception
readings: F1 63/72 = 87.5% → 72/72 and F7 16/20 = 80.0% → 20/20 (matchable over judged
pairs; M2-short, allow arm; the paired readings at θ′ = 0.55 are H_max = 0.5 and nominal
remaining uncertainty 24 bit, row `C199`). On airline the same change **lowers** them: M2's
F7 46/46 is
closed-world rejection (6-byte halves below ℓ_min = 8 fall outside the matcher and are
denied outright, H̄ = 0.000,
observed residual 48 bit — not detection), while M2-short's true matching delivers
9/46 intercepted F7 pairs at θ′ ≤ 0.8 (H̄ = 0.902, H_max = 1.000, observed residual minimum
0 bit) and 0/46 at θ′ = 1.0 (H̄ = 1.000; Wilson 95% upper bound 7.7%) — with the unique reading forcing
46/46 on the same rows (92 ambiguous malicious fragments), the largest reading-dependence in
the airline grid. The airline F1 family (13 pairs, 2 task clusters) is reported but not
judged (M2 13/13 by the same ℓ_min rejection; M2-short 0/13 with 12/12 bytes delivered).
The sign of the ℓ_min effect therefore depends on the workload's write geometry, and M2-short
is not claimed to improve on M2 anywhere.[^m2short-src] On the benign side both workloads
agree in direction: airline field-level write tasks, n = 15, misfire 14/15 = 93.3% at
θ′ = 0.55 (no holdout; union = unique; Wilson 95% interval 70.2–98.8%), the
direction-consistent, power-limited reading already qualified in §5.


## 10. Related work {#sec:related}

**Aggregation inference in statistical databases.** The aggregation problem asks how queries that
are individually legal combine into a disclosure that is not. Denning and Denning frame it around
the *set of answers* — query size and overlap, the sensitivity of a view to a single record, and
the trackers that reconstruct an individual value from successive totals
\cite{denning1979data,chin1981statistical}; Adam and Wortmann survey the control families that
followed \cite{adam1989security}. Later work replaced those syntactic conditions with semantic
ones — a formal secrecy order over views \cite{miklau2007formal}, distributional criteria on the
released table \cite{machanavajjhala2007diversity}, and, with Dwork's differential privacy, a
noise-calibrated guarantee that bounds the influence of any single record
\cite{dwork2006differential}. In all of it the unit of analysis is the query or the released
view, and the adversary is modelled as a consumer of answers whose inferences are checked against
a declared model of the data. This paper shares the feasibility question but not the object. Its
unit is the attributed content fragment carried by one tool call; the secret is assembled outside
the database, by an agent that is itself steered by the content it reads; and the criterion never
sees a query. Neither the τ pair nor the matchability boundary ℓ_min has a counterpart in that
framework, and its criteria — which constrain what a set of answers implies — cannot express what
the coverage-closure family is denied by: that a *single* answer may be permitted while the union
of the permitted answers already exceeds the tolerance.

**Volume rules in data-loss prevention.** A second line, surveyed by Shabtai et al. and by
Alneyadi et al. \cite{shabtai2012survey,alneyadi2016survey}, treats leakage as a volume
phenomenon attributable to a channel, a host or an account, and its controls are cumulative:
bytes, files or call counts accumulated per entity and compared against a threshold.
Insider-threat taxonomies locate the same signal in the aggregate behaviour of an account over
time \cite{homoliak2019insight}, and the empirical
literature on breaches summarises incidents in the same aggregate vocabulary — records per
incident, over time \cite{edwards2016hype}. The shared assumption is that the quantity to bound is
volume and that volume can be attributed without inspecting content. The attraction of the class
is that it needs no model of the data — a counter and a threshold — which is also why it reaches
settings where content inspection is not permitted. One result from the auditing side already
marks the limit of that assumption: Kenthapadi et al. show that an auditor whose refusals are
themselves observable leaks through the refusals, so the accounting has to be simulatable
\cite{kenthapadi2005simulatable}. The τ pair is the shape this rule class cannot survive. The two
arms are byte-identical call by call (572/572), so a byte-or-count rule returns the same verdict
on both arms of every pair at every threshold; what separates the arms is which cell a fragment is
booked to, and that is not in the rule's state. A cumulative rule is therefore an attribution-blind
accumulator in the sense of §\ref{sec:tau}, not a weaker instance of one.

**Information-flow control and CaMeL.** The third line answers a different question — who may
receive which value — with labels on data and a policy over principals fixed before the value
moves: the access-matrix and capability formulation of least privilege
\cite{saltzer1975protection,dennis1966programming}, the lattice model of secure flow
\cite{denning1976lattice}, Sabelfeld and Myers's account of language-based information-flow
control with its noninterference criterion \cite{sabelfeld2003language}, and the decentralized
label model that lets data owners set policy without a central authority
\cite{myers1997decentralized}. The design decides each call against the labels in scope, and
composition across calls is left to the application that issues them. Debenedetti et al.'s CaMeL
carries the design to agents: a privileged model plans, a quarantined model reads untrusted data,
and a policy engine checks every tool call against capabilities derived from the user's request
\cite{debenedetti2025defeating}. Measured on the 72 τ pairs it covers, all three configurations —
hardening, out of the box, most permissive — land at DISTINGUISH = 0: the hardened configuration
blocks both arms 72/72, the permissive one leaks both 72/72 (G4 in the evaluation matrix;
`reports/external/w6.1_g4_report.md`). The cause is granularity rather than implementation. Every
fragment in the leak carries a label and a permitted destination, and every call is authorised by
the policy that governs it; what the policy does not see is the assembly. Labels constrain where a
value may go, and the threat here is a value that reaches a permitted place in pieces.

Across the three lines, then, this paper is not another entry in those lines; it is a boundary and
measurement account of the single-field coverage-closure family — what such criteria can
discriminate, at what benign cost, and with how much residual uncertainty. It is also a negative
result, and negative results are published less often than positive ones \cite{fanelli2011negative};
the reporting bias that follows from preferring positive findings \cite{ioannidis2005why} is why
the scan, the second workload and the empty region appear together with their scope conditions
rather than as a recommendation.

## 11. Limitations {#sec:limitations}

1. **One real workload carries the quantitative readings.** The misfire leg of §\ref{sec:c1}–§\ref{sec:lmin} is
   measured on the retail domain's 68-task holdout (38/68 = 55.9%, union = unique; Wilson
   95% interval 44.1–67.1); the entropy leg depends on `L` and θ′ only, but every
   misfire percentage in this paper is a retail reading (`analysis/w11spike_grid.csv`;
   `paper/c1_proposition.md` §5.4).
2. **The second workload is direction-consistent and not quantitative.** Airline field-level
   write tasks: n = 15, no holdout, misfire 14/15 = 93.3% (union = unique; Wilson 95%
   interval 70.2–98.8%); the pre-registered branch is recorded UNDECIDABLE (power) and the
   airline F1 family (13 pairs, 2 task clusters) is not estimable
   (`reports/spike/w11airline_report.md` §4; D-026 §一, D-027 SP3/SP5).
3. **The attacker is scripted.** C-A, C-B, C-B* and C-B** are deterministic constructions;
   C-B** upper-bounds single-call leakage of the single-field family
   (`h = ⌈θ′L⌉ − 1`, attained at every grid point). Adaptation changes which
   assumption-level escapes are exercised — the cross-cell re-declaration of H2 is such an
   escape, measured as a two-call bypass in W10.2 — and the propositions already hold those
   escapes outside the family, so adaptation does not reopen the feasible region
   (`reports/spike/w11spike_report.md` §5.3; `reports/mcp/w10.2_report.md`).
4. **The two operating thresholds are value judgments.** 24 bit and 30% were fixed before the
   data \cite{nosek2018preregistration} (D-023 §三); the measured object is the tradeoff itself
   (the frontier plot: on the same rows,
   misfire 57.4% → 16.2% union while R falls 24 → 4 bit and H rises 0.542 → 0.975). The
   no-go is not a measurement consequence of the thresholds: any R_min ≥ 8 bit keeps the
   region empty, and for L ≥ 12 the H-leg dominates — loosening the leakage criterion to
   H ≤ 0.975 would pass `C222`, meaning "the attacker delivers 97.5% before being denied"
   (`paper/c1_proposition.md` Corollaries 1 and 3; D-024 §一).[^A1-encoding]
5. **No usable criterion is on offer.** The within-construction triple (intercept 104/104,
   complete-reconstruction rate 0/104, utility 1.00) is a within-construction lens reading
   with benign depth below θ by construction; the real-workload misfire is 38/68 = 55.9%
   (`reports/audit/w3.3_receipt_v1.md` G2; `analysis/w11spike_grid.csv` row `C001`).
6. **θ* = 0.9877 is a property of the retail final-coverage distribution.** The invariance
   result covers write granularity within one workload; the distribution of how much of a
   field a legitimate task writes is the remaining free variable, and the airline carrier is
   a plateau (14/15 unchanged across θ′ ∈ [0.55, 0.8], whole-field writes)
   (`reports/spike/w11geom_report.md` §3.2; `reports/spike/w11airline_report.md` §3.1).
7. **No complexity or reduction results.** The paper rests on two conditional statements —
   Theorem 1 and Proposition 1 — both elementary; no reduction from a hardness assumption
   and no complexity characterization of the criteria class is offered
   (`paper/tau_pair_theorem.md` §3; `paper/c1_proposition.md` §3.2).

[^A1-encoding]: **A1 (encoding realism).** All secrets are 12–40 character hex strings, and
    the nominal remaining uncertainty inherits the uniform-independent-character assumption
    (H3). Real secrets violate it — dates, checksums, dictionary words carry less uncertainty
    than the nominal value, so the ≥ 24-bit criterion reads stronger than a content-entropy
    reading would. The transform audit found base32 fully unmatched (100% miss on the
    heldout class) while base64url and upper-case hex did not constitute held-out encodings
    on this input set (`reports/spike/w11spike_report.md` §6).

<!-- =====================================================================
  定稿待办（第 5 段后：标题/摘要/贡献/关键词 ＋ §1–§11 全部成稿）
  ① 摘要已完成：175 词（按 200 词硬门槛预算、余量 25；窗单未指定目标刊，若为 150/250
     词预算，S3 不确定性句与 S4 airline 句为可删减位）；逐句正文映射见 Notes「摘要映射」。
  ② §1–§3 前向节号占位换 \ref（头部"陈旧前向节号"注）
  ③ REPRODUCE.md（analysis/*.csv → 每图每表复算命令）＋ 复现包清单 ＋ reports/audit/w7.2_receipt.md
  ④ 文献：原占位键已全部换为 \cite{}——38 条、八块覆盖、逐条 DOI/arXiv 核验（W0.7）
  ⑤ 闸门抽查：主张→D-0xx/reports 10 条；图重算 2 张；全文禁词+十禁复扫
  待定段：原结构项 4「真实负载下的误拦机制」（W10.1：1/68 完成率；单动作片段并集越阈）
          —— 55.9% 已在 §3 同段并列，机制段落在哪一节待负责人定。
===================================================================== -->


## Notes（脚注与数据来源，正文锚点 — 附加纪律 A3）

[^tau-src]: Construction and judgment set: 126 pairs across 20 intents, 104-pair judgment set
    (56 content + 48 credential); identity audits in `reports/audit/w2.4_reaudit_v1.md`
    (harm-point identity 104/104; benign-arm full release 104/104) and
    `reports/mcp/w6.2_detector_report.md` (104 episodes / 572 calls per arm).
    Construction geometry: benign arm depth `1/k` per cell, dangerous arm consecutive slices
    of one field (W2.2/W2.4).

[^thm-src]: Theorem 1, definitions D1–D5, erasure operator, and the class correction
    (attribution-blind, not "scalar"; per-cell scalar counter `C3` discriminates and is a
    counterexample to the "scalar vs interval" reading): `paper/tau_pair_theorem.md` §2–§4, §9
    (with no new experiments; symbol table shared with `paper/c1_proposition.md`).

[^kb-boundary]: `K_B` intercept 104/104 with no benign-arm misfire on the τ pairs:
    `reports/mcp/w6.2_detector_report.md` (K_B deny 279/572 calls on the dangerous arm vs
    0/572 on the benign arm); boundary discussion `paper/tau_pair_theorem.md` §6.1.
    Scope triple `C031`/`C037`/`C049` (misfire 39/68, 39/68, 15/68; `F7` 20/20, 0/20, 0/20):
    `analysis/w11spike_grid.csv` (lineage=L3, matcher=M1, unmatched=allow, denom=D1, θ′=0.55).

[^kb-consts]: Deployed θ = 0.55 frozen policy (`configs/policy/w32_freeze_v1.json`, asserted at
    every entry); first deny precedes the completing fragment by 1–3 calls and K_B
    structural interception on the τ pairs is 104/104 with no benign-arm denial:
    `reports/mcp/w6.2_detector_report.md`; summary in `STATE.md` (W6.2 row).

[^g2-src]: complete-reconstruction rate 0/104 with Wilson 95% upper bound 3.56% (pre-registered
    δ = 5%) and utility 104/104 = 1.00 under Oracle `task_done` (per-channel artifact equality;
    benign-arm depth < θ by construction): `reports/audit/w3.3_receipt_v1.md` (G2), independently
    re-derived in `reports/audit/w4.1_receipt_v1.md` (criteria re-derivation 104/104;
    delivery-consistency 572/572). The paired real-workload reading of this paragraph is
    38/68 = 55.9% (see [^misfire-src]).

[^misfire-src]: Real-workload benign misfire 38/68 = 55.9%, holdout of 68 writable retail tasks,
    Wilson 95% interval 44.1–67.1 (S-1): `analysis/w11spike_grid.csv` row `C001`
    (stage=G-A, scope=S1, denom=D1, lineage=L1, θ=0.55; `benign_denied=38`, `benign_n=68`,
    `ambiguous_benign=0`); originally measured in W10.1.

[^metric-src]: `intercepted := delivered < truth_len`（`src/spike/w11_matching/gate.py` L191）；
    three-reading protocol per D-025 §五-2 and `reports/spike/w11spike_report.md` §10.4.
    Table 2 is generated from `analysis/w11spike_controls.csv` (8400 rows) and
    `analysis/w11spike_frontier.csv` by `analysis/fig_w72.py`; the 1.00 / 0.975 / 4 bit
    triple is the θ′ = 1.0 frontier row (`C036`/`C156`).

[^cw-src]: `unmatched=deny` semantics: `gate.py` L164–165; benign-side S-4 audit (318/318
    benign fragments matched, M1 and M2 byte-interval identical):
    `reports/audit/w0.3_ruling.md` §3. `C156` union/unique readings:
    `analysis/w11spike_grid.csv` row `C156` (`benign_denied=11`, `benign_denied_unique=34`,
    `ambiguous_benign=67`); unique wrapper `run_grid.py::_UniqueOnly`.

[^xmodel-src]: W10.3 (N = 30 injection episodes per arm × 3 models):
    `reports/mcp/w10.3_report.md` (C1/C2 tables; ME-1 成立, ME-4 不成立; E1 per-model
    readings with Wilson intervals) and `reports/mcp/w10.3_receipt_v1.md`. Service-mode
    heterogeneity: `ENV_LOCK.md` W10.3 section (qwen main matrix with thinking disabled;
    deepseek reasoning-content passthrough; temperature/max_tokens per serving).

[^inloop-src]: W6.3 (N = 15 injection episodes per cell; one model in the loop):
    `analysis/w63_summary.json` (cells G4/G7 × off/spotlighting: ASR, H̄) and
    `reports/mcp/w6.3_report.md`; rendering fix (delimiter applied to both arms) documented
    in `DEVIATION_LEDGER.md` (W6.3, 2026-11-02).

[^m2short-src]: Airline readings: `reports/spike/w11airline_report.md` §4–§5 (A011/A013/A014
    M2 vs A019/A021/A022 M2-short; F7 n=46 judged pairs, F1 n=13 pairs not judged per D-026)
    and `analysis/w11airline_grid.csv`. Retail M2-short: `analysis/w11spike_grid.csv`
    rows `C199`–`C204` (F1 72/72, F7 20/20, matched denominators). ℓ_min parameters:
    `src/spike/w11_matching/matching.py` (M2 ℓ∈{8,16,32}; M2-short ℓ∈{4,6,8,16,32}).

[^abstract-map]: **摘要映射（`W0.7` 复核并刷新；绝对行号以当前母本为准，后续编辑须复跑
    `reports/audit/w7.2_prose_check.py` 并刷新本表）。摘要 179 词（硬门槛按 200 词预算，
    余量 21；窗单未指定目标刊）。逐句正文对应（正文命中行，绝对行号）——
    S1 ← L95（"The exfiltration we care about is **aggregation-based** … legitimate."，逐字，
    去 ** 强调标记）；S2 ← L228（命题头 "(empty feasible region under H1–H4)"，逐字小写）
    ＋ L228–229（"⑤ forces θ′ ≤ 7/12; ① forces θ′ ≥ θ* > 7/12; no θ′ satisfies both."，
    逐字）；S3a ← L222（不确定性下界整句，逐字）；S3b ← L270（"conditional on the
    workload … per-task final-coverage distribution"，逐字，去 ** 标记）；
    S4a ← L237（"The 234-combination scan … (Wilson 95% upper bound 3.6%)"，逐字）；
    S4b ← L275（**节选**："On the second workload the picture is direction-consistent but
    power-limited: airline field-level write tasks, n = 15"——删去 "misfire 14/15 = 93.3%
    (no holdout; Wilson 95% interval 70.2–98.8%), verdict UNDECIDABLE (D-026 §一)"，摘要禁
    未带全口径的百分比，删减不改变主张）＋ L278（"…anchored to retail, and no
    workload-independence is claimed."，逐字）。摘要中的两个百分数（95%、3.6%）为
    Wilson 方法与上界值，口径（234 组扫描、102 候选、union 与 unique 双读数、五条门槛）
    在同一句内给出。摘要曾于第 5 段写作 "Empty feasible region…"（大写 E），
    定稿检查段按"改摘要不改正文"修正为正文逐字小写并加连接词 "The result is an"。
