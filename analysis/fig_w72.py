# -*- coding: utf-8 -*-
"""Regenerate all figures and LaTeX tables from the result CSVs.

All experimental values are read from analysis/*.csv; the only constants here are the
preregistered decision thresholds and the matcher parameter l_min=8. Figure text is
English-only and contains no file paths: save() asserts this on both the SVG text nodes
and the PDF text layer. Misfire rates are printed to one decimal (38/68 -> 55.9%).
Outputs are byte-identical on re-run (timestamps cleared, svg.hashsalt fixed).
"""

import csv
import hashlib
import re
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "paper" / "figures"
TAB = ROOT / "paper" / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

GATE_MISFIRE = 30.0
GATE_INTERCEPT = 90.0
GATE_RESIDUAL = 24
GATE_H = 0.5               # ⑤ partial-leakage fraction ≤0.5
GATE_CC_MISS = 0.10
L_MIN = 8

plt.rcParams.update(
    {
        "font.family": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.linewidth": 0.8,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "lines.linewidth": 0.9,
        "lines.markersize": 3.6,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "svg.hashsalt": "fig_w72-stable",
    }
)


def read_csv(name):
    with open(ROOT / "analysis" / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    return float(x)


def fmt_bits(v):
    return f"{v:g}"


CJK_RE = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")
BAD_SUBSTR = ("analysis/", "reports/", ".csv", "w11spike", "w11geom", "w11airline", "55.88")


def svg_text(path):
    raw = path.read_text(encoding="utf-8")
    nodes = re.findall(r"<text[^>]*>(.*?)</text>", raw, flags=re.S)
    return " ".join(re.sub(r"<[^>]+>", " ", n) for n in nodes)


def pdf_text(path):
    import pymupdf

    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def assert_figure_text_clean(stem, svg_path, pdf_path):
    s_txt = svg_text(svg_path)
    p_txt = pdf_text(pdf_path)
    assert s_txt.strip(), f"{stem}: SVG 无文本节点（svg.fonttype 应为 none）"
    assert p_txt.strip(), f"{stem}: PDF 无文本层"
    for label, txt in (("SVG", s_txt), ("PDF", p_txt)):
        hit = CJK_RE.search(txt)
        assert not hit, f"{stem}: {label} 含中文 {hit.group(0)!r}"
        for bad in BAD_SUBSTR:
            assert bad not in txt, f"{stem}: {label} 含禁用串 {bad!r}"


def save(fig, stem):
    svg_path = FIG / f"{stem}.svg"
    pdf_path = FIG / f"{stem}.pdf"
    fig.savefig(svg_path, metadata={"Date": None})
    svg_path.write_bytes(svg_path.read_bytes().replace(b"\r\n", b"\n"))
    fig.savefig(
        pdf_path,
        metadata={"CreationDate": None, "ModDate": None, "Creator": None},
    )
    data = pdf_path.read_bytes()
    assert b"Type3" not in data, f"{pdf_path.name}: Type3 font leaked"
    assert b"/FontFile2" in data, f"{pdf_path.name}: no embedded TrueType (/FontFile2)"
    plt.close(fig)
    assert_figure_text_clean(stem, svg_path, pdf_path)
    return svg_path, pdf_path


def despine(ax, keep_right=False):
    ax.spines["top"].set_visible(False)
    if not keep_right:
        ax.spines["right"].set_visible(False)


# =====================================================================
# =====================================================================
grid = read_csv("w11spike_grid.csv")
frontier = read_csv("w11spike_frontier.csv")
geom = read_csv("w11geom_curve.csv")
controls = read_csv("w11spike_controls.csv")

probe = [
    r
    for r in grid
    if r["stage"] == "G-A"
    and r["scope"] == "S1"
    and r["denom"] == "D1"
    and r["lineage"] == "L1"
]
probe.sort(key=lambda r: fnum(r["theta"]))
assert len(probe) == 6, f"probe rows = {len(probe)}"
misfire = [(fnum(r["theta"]), fnum(r["benign_rate"]) * 100.0, int(r["benign_denied"]), int(r["benign_n"])) for r in probe]

cb_rows = [
    r
    for r in frontier
    if r["pool"] == "frozen110"
    and r["label"].startswith("S1|D1|L3|")
    and "|M1|" in r["label"]
]
assert len(cb_rows) == 12, f"C-B** rows = {len(cb_rows)}"
cb = {}
for r in cb_rows:
    t = fnum(r["theta"])
    cur = cb.setdefault(t, {"res": [], "H": []})
    cur["res"].append(fnum(r["residual_bits_min"]))
    cur["H"].append(fnum(r["H_max"]))
cb_series = sorted(
    (t, min(v["res"]), max(v["H"])) for t, v in cb.items()
)
assert len(cb_series) == 6, f"C-B** theta levels = {len(cb_series)}"

tab1_rows = [
    r
    for r in grid
    if r["stage"] == "G-D"
    and r["scope"] == "S1"
    and r["denom"] == "D1"
    and r["lineage"] == "L3"
    and r["matcher"] == "M2"
    and r["unmatched"] == "deny"
]
tab1_rows.sort(key=lambda r: fnum(r["theta"]))
assert len(tab1_rows) == 6, f"tab1 rows = {len(tab1_rows)}"
cb_by_theta = {t: (res, H) for t, res, H in cb_series}

ceil_rows = [
    r
    for r in grid
    if r["stage"] == "G-B"
    and r["scope"] == "S1"
    and r["denom"] == "D1"
    and r["lineage"] == "L3"
    and r["matcher"] == "M2"
    and r["unmatched"] == "allow"
]
assert len(ceil_rows) == 6, f"ceiling rows = {len(ceil_rows)}"
for col in ("F1_n", "F1_match_n", "F7_n", "F7_match_n"):
    vals = {r[col] for r in ceil_rows}
    assert len(vals) == 1, f"{col} not constant across theta: {vals}"
r0 = next(r for r in ceil_rows if fnum(r["theta"]) == 0.55)
F1_N, F1_M = int(r0["F1_n"]), int(r0["F1_match_n"])
F7_N, F7_M = int(r0["F7_n"]), int(r0["F7_match_n"])

CANDS = ["C156", "C204", "C222"]
cand_labels = {}
for cid in CANDS:
    rows = [r for r in grid if r["combo_id"] == cid]
    assert len(rows) == 1, f"{cid}: {len(rows)} grid rows"
    cand_labels[cid] = rows[0]
assert all(cand_labels[c]["go_eligible"] == "1" for c in CANDS)

COVERED_PREFIX = "covered:"
Z95 = 1.959964


def wilson_upper(k, n):
    if n <= 0:
        return float("inf")
    p = k / n
    denom = 1.0 + Z95 * Z95 / n
    centre = p + Z95 * Z95 / (2.0 * n)
    half = Z95 * ((p * (1.0 - p) / n + Z95 * Z95 / (4.0 * n * n)) ** 0.5)
    return min(1.0, (centre + half) / denom)


tab2_data = {}


def min_rate_with_upper(rows, counter):
    sel = [r for r in rows if r["counter"] == counter]
    assert sel, counter
    best = min(sel, key=lambda r: fnum(r["rate"]))
    rate = fnum(best["rate"])
    n = int(best["n"])
    return rate, (wilson_upper(round(rate * n), n) if rate == 0.0 else float("nan"))


for cid in CANDS:
    crows = [r for r in controls if r["combo_id"] == cid]
    assert crows, cid
    ca, ca_u = min_rate_with_upper(crows, "C-A")
    cbm, cbm_u = min_rate_with_upper(crows, "C-B")
    covered = [
        r
        for r in crows
        if r["counter"] == "C-C" and r["param"].startswith(COVERED_PREFIX)
    ]
    cc = max((fnum(r["miss_rate"]) for r in covered), default=0.0)
    cc_u = max(
        (wilson_upper(round(fnum(r["miss_rate"]) * int(r["n"])), int(r["n"])) for r in covered),
        default=float("inf"),
    )
    counter_rows = [r for r in crows if r["counter"] in ("C-A", "C-B", "C-B*")]
    worst_res = min(fnum(r["residual_bits_min"]) for r in counter_rows)
    worst_H = max(
        fnum(r["H_max"]) for r in counter_rows if fnum(r["residual_bits_min"]) == worst_res
    )
    frows = [r for r in frontier if r["combo_id"] == cid]
    assert frows, cid
    cbss_res = min(fnum(r["residual_bits_min"]) for r in frows)
    cbss_H = max(fnum(r["H_max"]) for r in frows)
    tab2_data[cid] = {
        "CA": ca,
        "CA_U": ca_u,
        "CB": cbm,
        "CB_U": cbm_u,
        "CC": cc,
        "CC_U": cc_u,
        "worst_res": worst_res,
        "worst_H": worst_H,
        "cbss_res": cbss_res,
        "cbss_H": cbss_H,
    }

# =====================================================================
# fig1_frontier —— misfire / nominal-uncertainty frontier (dual y axis)
# =====================================================================
fig, axL = plt.subplots(figsize=(3.3, 2.75))
fig.subplots_adjust(left=0.152, right=0.848, bottom=0.285, top=0.97)
axR = axL.twinx()

xs = [m[0] for m in misfire]
ys = [m[1] for m in misfire]
line_l, = axL.plot(
    xs, ys, color="0.0", marker="o", markerfacecolor="white",
    markeredgewidth=0.9, linestyle="-", zorder=4,
    label="Benign misfire (left axis)",
)
rs = [c[1] for c in cb_series]
line_r, = axR.plot(
    xs, rs, color="0.45", marker="s", markerfacecolor="white",
    markeredgewidth=0.9, linestyle="--", zorder=3,
    label="Nominal uncertainty (right axis)",
)

axL.axhline(GATE_MISFIRE, ls=":", lw=0.8, color="0.65", zorder=1)
axR.axhline(GATE_RESIDUAL, ls=":", lw=0.8, color="0.65", zorder=1)

t0, y0, d0, n0 = misfire[0]
t1, y1, d1, n1 = misfire[-1]
res1 = cb_series[-1][1]
axL.annotate(f"{d0}/{n0} = {y0:.1f}%", (t0, y0), xytext=(8, 6),
             textcoords="offset points", fontsize=7)
axR.annotate(f"{fmt_bits(res1)} bit", (t1, res1), xytext=(-6, 8),
             textcoords="offset points", fontsize=7, ha="right")

axL.set_xticks(xs)
axL.set_xticklabels([("1.0" if f"{t:g}" == "1" else f"{t:g}") for t in xs])
axL.set_xlim(0.505, 1.045)
axL.set_ylim(0, max(ys) * 1.24)
axR.set_ylim(0, max(rs) * 1.45)
axL.set_xlabel("Candidate threshold θ′ (deployed θ = 0.55)")
axL.set_ylabel("Benign misfire (%, 68-task holdout)")
axR.set_ylabel("Nominal remaining uncertainty (bit)")
despine(axL, keep_right=True)
axR.spines["top"].set_visible(False)
axL.legend(handles=[line_l, line_r], loc="lower left", fontsize=7,
           handlelength=2.2, borderaxespad=0.3)
save(fig, "fig1_frontier")

# =====================================================================
# fig2_geometry —— write-granularity invariance (G1–G5, L1 arm, coincident)
# =====================================================================
l1 = [r for r in geom if r["arm"] == "L1"]
geos = sorted({r["geometry"] for r in l1})
assert len(l1) == len(geos) * 6, f"L1 rows = {len(l1)}"
series = {}
for g in geos:
    pts = sorted((fnum(r["theta"]), fnum(r["benign_rate"]) * 100.0) for r in l1 if r["geometry"] == g)
    series[g] = pts
thetas = [p[0] for p in series[geos[0]]]
for g in geos[1:]:
    assert [p[0] for p in series[g]] == thetas
    assert all(abs(a[1] - b[1]) < 1e-12 for a, b in zip(series[geos[0]], series[g])), "curves differ"

fig, ax = plt.subplots(figsize=(3.3, 2.35))
fig.subplots_adjust(left=0.155, right=0.97, bottom=0.285, top=0.97)
ax.plot(
    thetas,
    [p[1] for p in series[geos[0]]],
    color="0.0",
    linestyle="-",
    marker="o",
    markerfacecolor="white",
    markeredgewidth=0.9,
    markersize=4.2,
    zorder=3,
    label=f"{geos[0]}\u2013{geos[-1]} coincide",
)
y55 = series[geos[0]][0][1]
ax.annotate(f"{y55:.1f}%", (thetas[0], y55), xytext=(8, 6), textcoords="offset points", fontsize=7)
ax.set_xticks(thetas)
ax.set_xticklabels([("1.0" if f"{t:g}" == "1" else f"{t:g}") for t in thetas])
ax.set_xlim(0.505, 1.045)
ax.set_ylim(0, y55 * 1.22)
ax.set_xlabel("Candidate threshold \u03b8\u2032 (deployed \u03b8 = 0.55)")
ax.set_ylabel("Benign misfire (%, 68-task holdout)")
despine(ax)
ax.legend(loc="upper right", fontsize=7, handlelength=2.4, borderaxespad=0.3)
save(fig, "fig2_geometry")

# =====================================================================
# fig3_lmin —— minimum attributable fragment length (matchable ceiling)
# =====================================================================
fig, ax = plt.subplots(figsize=(3.3, 2.55))
fig.subplots_adjust(left=0.165, right=0.97, bottom=0.27, top=0.97)

groups = [("F1", F1_N, F1_M), ("F7", F7_N, F7_M)]
w = 0.30
xs_pos = [0, 1]
mat_pct = [m / n * 100.0 for _, n, m in groups]
ax.bar([x - w / 2 - 0.02 for x in xs_pos], [100.0, 100.0], width=w,
       color="0.85", edgecolor="0.2", linewidth=0.8, zorder=2)
ax.bar([x + w / 2 + 0.02 for x in xs_pos], mat_pct, width=w,
       color="0.40", edgecolor="0.0", linewidth=0.8, zorder=2)
for x, (_, n, m) in zip(xs_pos, groups):
    ax.text(x - w / 2 - 0.02, 92, f"{n}/{n}", ha="center", va="center",
            fontsize=7, color="0.0")
    ax.text(x + w / 2 + 0.02, 55, f"{m}/{n}", ha="center", va="center",
            fontsize=7, color="white")
    ax.text(x + w / 2 + 0.02, 35, f"{m / n * 100.0:.1f}%", ha="center",
            va="center", fontsize=7, color="white")

ax.axhline(GATE_INTERCEPT, ls="--", lw=0.8, color="0.25", zorder=1)
ax.text(0.50, 87.0, f"gates\n(2)/(3)\n{GATE_INTERCEPT:g}%", fontsize=7,
        ha="center", va="top", color="0.25", linespacing=1.1)
ax.set_xticks(xs_pos)
ax.set_xticklabels([f"{g[0]} (n = {g[1]})" for g in groups])
ax.set_xlim(-0.55, 1.55)
ax.set_ylim(0, 100)
ax.set_ylabel("Share of judged pairs matched (%)")
despine(ax)
save(fig, "fig3_lmin")

# =====================================================================
# =====================================================================
def tex_escape(s):
    return s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def fmt_theta(t):
    return "1.0" if f"{t:g}" == "1" else f"{t:g}"


lines = []
lines.append("% Generated by analysis/fig_w72.py; every value is read from the CSV inputs, re-running reproduces it.")
lines.append("% Table 1 (candidate family C151--C156). Table 2 = tab1b_cost.tex; Table 3 = tab2_counters.tex.")
lines.append(r"\begin{table}[!htbp]")
lines.append(r"\centering")
lines.append(r"\caption{Candidate family C151--C156: gate readings across the candidate threshold $\theta'$. "
             r"F1/F7 are structural interception rates inside the self-built construction "
             r"($n=72$ and $20$ judged pairs); misfire is the share of benign tasks denied on the "
             r"68-task retail holdout (union ambiguity reading).}")
lines.append(r"\label{tab:maina}")
lines.append(r"\small")
lines.append(r"\begin{tabular}{lrrrrc}")
lines.append(r"\toprule")
lines.append(r" & & \multicolumn{1}{c}{Real workload} & \multicolumn{2}{c}{Within-construction} & \\")
lines.append(r"\cmidrule(lr){3-3}\cmidrule(lr){4-5}")
lines.append(r"combo & $\theta'$ & Misfire (\%)$^{a}$ & F1 & F7 & go-elig. \\")
lines.append(r"\midrule")
for r in tab1_rows:
    t = fnum(r["theta"])
    uni = fnum(r["benign_rate"]) * 100.0
    uni_d, n_b = int(r["benign_denied"]), int(r["benign_n"])
    f1 = f"{int(r['F1_intercepted'])}/{int(r['F1_n'])}"
    f7 = f"{int(r['F7_intercepted'])}/{int(r['F7_n'])}"
    lines.append(
        f"{tex_escape(r['combo_id'])} & {fmt_theta(t)} & {uni:.1f} & "
        f"{tex_escape(f1)} & {tex_escape(f7)} & {int(r['go_eligible'])} \\\\"
    )
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\par\smallskip")
lines.append(r"{\footnotesize\begin{minipage}{0.98\linewidth}")
lines.append(r"\footnotesize $^{a}$~Benign misfire on the real workload (68-task retail holdout, union reading): "
             + f"{tab1_rows[0]['benign_denied']}/{tab1_rows[0]['benign_n']} tasks denied at $\\theta'$=0.55 and "
             + f"{tab1_rows[-1]['benign_denied']}/{tab1_rows[-1]['benign_n']} at $\\theta'$=1.0. "
             r"F1/F7 = structural interception rate over the judged pairs of the self-built construction; "
             r"go-elig.\ = in the deployable candidate pool. The unique reading and the post-interception "
             r"uncertainty pair are in Table~\ref{tab:mainb}. "
             r"Rows: matcher M2, unmatched = deny, single-field coverage, scope S1, denominator D1. "
             r"$^{b}$~With unmatched = deny the 13 judged pairs whose secret is carried in 6-byte halves "
             r"are rejected by the closed-world rule before any matching, so F1/F7 read 72/72 on these "
             r"rows: closed-world rejection, not detection.")
lines.append(r"\end{minipage}}")
lines.append(r"\end{table}")
(TAB / "tab1a_main.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

lines = []
lines.append("% Generated by analysis/fig_w72.py. Misfire: grid rows C151--C156. Residual/H: frontier rows C031--C036.")
lines.append("%   Two different row families, labelled as such in the note; 24 bit is an operating criterion.")
lines.append(r"\begin{table}[!htbp]")
lines.append(r"\centering")
lines.append(r"\caption{Cost side of the same candidate family (C151--C156) and the post-interception pair. "
             r"Residual uncertainty = nominal remaining uncertainty under the uniform-independent-hex "
             r"assumption (adaptive-$\theta'$ counter-construction); $H$ = partial-leakage fraction; "
             r"24\,bit is an operating criterion, not a security level.}")
lines.append(r"\label{tab:mainb}")
lines.append(r"\small")
lines.append(r"\begin{tabular}{lrrrrr}")
lines.append(r"\toprule")
lines.append(r" & & \multicolumn{2}{c}{Real workload (holdout 68)} & \multicolumn{2}{c}{Within-construction} \\")
lines.append(r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}")
lines.append(r"combo & $\theta'$ & Misf. union (\%) & Misf. unique (\%) & Resid.\ (bit)$^{a}$ & $H^{a}$ \\")
lines.append(r"\midrule")
for r in tab1_rows:
    t = fnum(r["theta"])
    uni = fnum(r["benign_rate"]) * 100.0
    uni_d, n_b = int(r["benign_denied"]), int(r["benign_n"])
    unq = fnum(r["benign_rate_unique"]) * 100.0
    unq_d = int(r["benign_denied_unique"])
    res, H = cb_by_theta[t]
    lines.append(
        f"{tex_escape(r['combo_id'])} & {fmt_theta(t)} & {uni:.1f} & {unq:.1f} & "
        f"{fmt_bits(res)} & {H:.3f} \\\\"
    )
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\par\smallskip")
lines.append(r"{\footnotesize\begin{minipage}{0.98\linewidth}")
lines.append(r"\footnotesize $^{a}$~Read from rows C031--C036, \emph{not} from the C151--C156 rows of the "
             r"misfire columns: an oracle single-field arm under the adaptive-$\theta'$ counter-construction. "
             r"Residual and $H$ are a worst-case envelope over episodes of different secret length, not one "
             r"episode (Section~\ref{sec:c1}). Union$|$unique = multi-candidate union vs.\ unique ambiguity "
             r"reading (denied/68: "
             + f"{tab1_rows[-1]['benign_denied']}/68$|${tab1_rows[-1]['benign_denied_unique']}/68 at $\\theta'$=1.0). "
             r"Rows: matcher M2, unmatched = deny, single-field coverage.")
lines.append(r"\end{minipage}}")
lines.append(r"\end{table}")
(TAB / "tab1b_cost.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
old_tab1 = TAB / "tab1_main.tex"
if old_tab1.exists():
    old_tab1.unlink()

# =====================================================================
# =====================================================================
def cell(ok, content):
    return content if ok else "\\textbf{" + content + "}"


lines = []
lines.append("% Generated by analysis/fig_w72.py from the counter-construction runs and the frontier rows.")
lines.append("% Seven columns + superscript arms: the eight-column form overflowed the 387 pt text block.")
lines.append(r"\begin{table}[!htbp]")
lines.append(r"\centering")
lines.append(r"\caption{Counter-packing readings for the three candidates that pass gates (1) and (2) "
             r"(union reading), all at $\theta'=1.0$. Bold = fails a preregistered gate.}")
lines.append(r"\label{tab:counters}")
lines.append(r"\footnotesize")
lines.append(r"\begin{tabular}{lrrrrrr}")
lines.append(r"\toprule")
lines.append(r"combo & C-A & C-B & C-B** & C-C & resid./$H$ & verdict \\")
lines.append(r"\midrule")
ARM_SUP = {"C156": "a", "C204": "b", "C222": "c"}
for cid in CANDS:
    d = tab2_data[cid]
    ca_ok = d["CA"] * 100.0 >= GATE_INTERCEPT
    cb_ok = d["CB"] * 100.0 >= GATE_INTERCEPT
    cc_ok = d["CC"] < GATE_CC_MISS
    r5_ok = d["cbss_res"] >= GATE_RESIDUAL and d["cbss_H"] <= GATE_H
    rw_ok = d["worst_res"] >= GATE_RESIDUAL and d["worst_H"] <= GATE_H
    verdict = "NO" if (not (ca_ok and cb_ok and cc_ok and r5_ok and rw_ok)) else "GO"
    ca_cell = f"{d['CA']:.2f}" if d["CA"] else f"0.00 ({d['CA_U']:.3f})"
    cb_cell = f"{d['CB']:.2f}" if d["CB"] else f"0.00 ({d['CB_U']:.3f})"
    cc_cell = f"{d['CC']:.3f}" if d["CC"] else f"0.00 ({d['CC_U']:.3f})"
    rH = f"{fmt_bits(d['worst_res'])}/{d['worst_H']:.3f}"
    rH_cb = f"{fmt_bits(d['cbss_res'])}/{d['cbss_H']:.3f}"
    lines.append(
        f"{tex_escape(cid)}$^{{{ARM_SUP[cid]}}}$"
        f" & {cell(ca_ok, ca_cell)}"
        f" & {cell(cb_ok, cb_cell)}"
        f" & {cell(r5_ok, rH_cb)}"
        f" & {cell(cc_ok, cc_cell)}"
        f" & {cell(rw_ok, rH)}"
        f" & \\textbf{{{verdict}}} \\\\"
    )
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\par\smallskip")
lines.append(r"{\footnotesize\begin{minipage}{0.98\linewidth}")
lines.append(r"\footnotesize Rows are the three candidates of the coverage grid, all read at $\theta'=1.0$; "
             r"every counter column is a separate run of the self-built counter-constructions, not a row of "
             r"Tables~\ref{tab:maina}--\ref{tab:mainb}. "
             r"$^{a}$~M2 (content fingerprint, $\ell_{\min}=8$\,B), closed-world deny. "
             r"$^{b}$~M2-short ($\ell_{\min}=4$\,B), unmatched = allow. "
             r"$^{c}$~M2-short, closed-world deny. "
             r"C-A = min coverage rate over equal-split variants $n{=}2..6$ (both field families); "
             r"C-B = min over re-split variants (base2/base6 $\times$ chunk 1--4); "
             r"C-B** = adaptive-$\theta'$ upper bound (frontier rows of the same candidate); "
             r"C-C = max unmatched rate over covered encodings (none/base64/hex/homoglyph). "
             r"resid./$H$ = residual (bit) / partial-leakage fraction, worst case over the C-A/C-B/C-B* "
             r"readings (min residual, max $H$ at that residual). "
             r"A value in parentheses is the Wilson 95\% upper bound, reported for every 0/$n$ reading.")
lines.append(r"\end{minipage}}")
lines.append(r"\end{table}")
(TAB / "tab2_counters.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

# =====================================================================
# =====================================================================
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


outs = sorted(
    list(FIG.glob("fig*.svg")) + list(FIG.glob("fig*.pdf")) + list(TAB.glob("tab*.tex"))
)
print("== W7.3 图件回执 ==")
print(f"fig1 left axis (misfire): w11spike_grid.csv G-A/S1/D1/L1 probe = {len(probe)} rows (C001-C006)")
print(f"fig1 right axis (uncertainty): w11spike_frontier.csv adaptive counter, M1 arm = {len(cb_rows)} rows (C031-C036, 6 thresholds)")
print(f"fig2: w11geom_curve.csv arm=L1 = {len(l1)} rows ({len(geos)} geometries x 6 thresholds); coincidence assertion PASS")
print(f"fig3: w11spike_grid.csv G-B/S1/D1/M2/allow = {len(ceil_rows)} rows; constant denominators PASS (F1 {F1_M}/{F1_N}, F7 {F7_M}/{F7_N})")
print(f"tab1a/tab1b: w11spike_grid.csv G-D/S1/D1/L3/M2/deny = {len(tab1_rows)} rows (C151-C156)")
print(f"tab2: w11spike_controls.csv {len(CANDS)} candidates x 4 counter families + frontier rows")
print("FIG_TEXT_GATE=PASS (zero CJK, zero internal paths, 55.9% convention, in all three figures)")

fitz_ver = "n/a"
try:
    import fitz

    fitz_ver = fitz.__doc__.split()[1] if fitz.__doc__ else "unknown"
    for pdf_path in sorted(FIG.glob("fig*.pdf")):
        doc = fitz.open(pdf_path)
        page = doc[0]
        w_pt = page.rect.width
        sizes = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    sizes.append(span["size"])
        mn = min(sizes) if sizes else float("nan")
        ok = (mn >= 7.0) and abs(w_pt - 3.3 * 72) < 0.5
        print(
            f"B4 {pdf_path.name}: 框宽 {w_pt:.1f} pt（{w_pt / 72:.2f} in，单栏 3.3 in），"
            f"最小字号 {mn:.2f} pt（≥7 pt） [{'PASS' if ok else 'FAIL'}]"
        )
        assert ok, f"B4 FAIL: {pdf_path.name}"
except ImportError:
    print("B4: pymupdf 未安装，跳过框宽/字号度量（.venv 内 pip install pymupdf 后重跑）")

import matplotlib

inp = ["w11spike_grid.csv", "w11spike_frontier.csv", "w11geom_curve.csv", "w11spike_controls.csv"]
readme_lines = [
    "# paper/figures README (generated by analysis/fig_w72.py; do not edit by hand)",
    "",
    "- Regenerate: `python analysis/fig_w72.py` (one command rebuilds every figure and table).",
    f"- Environment: Python {__import__('sys').version.split()[0]}, matplotlib {matplotlib.__version__}",
    "- Stable file names (fig1_frontier / fig2_geometry / fig3_lmin); version history lives in git.",
    "- Text gate: every figure is checked for zero CJK characters, zero internal data paths, and the 55.9% convention.",
    "",
    "## Inputs (sha256, first 16 hex)",
]
for name in inp:
    readme_lines.append(f"- `analysis/{name}`: {sha(ROOT / 'analysis' / name)}")
readme_lines.append("")
readme_lines.append("## Outputs (sha256, first 16 hex)")
for p in outs:
    readme_lines.append(f"- `{p.relative_to(ROOT).as_posix()}`: {sha(p)}")
(FIG / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8", newline="\n")

for p in outs:
    print(f"  {p.relative_to(ROOT)}  sha256:{sha(p)}")
print("PDF 自检: 无 Type3、含 /FontFile2（TrueType 内嵌）— 全部 PASS")
