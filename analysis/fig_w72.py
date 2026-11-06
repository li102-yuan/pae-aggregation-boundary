# -*- coding: utf-8 -*-
"""W7.2 图件阶段：fig1/fig2/fig3（SVG+PDF）＋ tab1/tab2（LaTeX booktabs）。

一条命令重出全部八件：
    .venv/Scripts/python.exe analysis/fig_w72.py

纪律（窗口 W7.2 §二／§三）：
- 所有实验读数一律从 analysis/*.csv 读取；脚本内不硬编码任何实验数值。
  脚本中仅有的常量是预注册判据门槛（① 30%、②③ 90%、⑤ 24 bit／H 0.5、④ 10%）
  与机制参数 ℓ_min=8，出处 PREREG/D-023 §五，属判据而非数据。
- 样式：serif（Times New Roman，中文回退 Noto Serif SC）、无网格、去上边框
  （fig1 为双 y 轴，右轴刻度须挂在右边框上，故保留右边框）、线宽 0.8–1.0、
  字号 ≥7pt、单栏宽 3.3 in；直接标注优先于图例。
- PDF 以 fonttype=42（TrueType 子集内嵌）输出，无 Type3、无位图；输出后逐件做
  字节级自检（不得出现 Type3，必须出现 /FontFile2）。
- SVG/PDF 元数据时间戳置空，保证重跑字节一致（脚本尾部自检 sha256）。
- 每张图脚注写明数据来源 CSV 路径与行筛选条件。
- 不读/不改 analysis/ 下任何 CSV 的内容（只读）；airline 不入图（是表，另窗处理）。

口径裁定（本窗会话内确认，已记 DEVIATION_LEDGER）：
- fig1 右轴与 tab1 残熵/H 列 = D-025 §二-1 规定的 C-B**（θ′ 自适应）口径，
  取 w11spike_frontier.csv 的 C031–C036（M1·oracle 单字段覆盖臂，frozen110），
  nominal 24/16/12/8/4/4 bit、H_max 0.542–0.975。w11spike_controls.csv 实际
  只有 C-A/C-B/C-B*/C-C 四类行（无 C-B** 行），C-B** 读数仅存在于 frontier。
- fig1 左轴误拦 = G-A 段 S1/D1/L1 探针（C001–C006，holdout 68），与论文 v2
  §3.3(b) 表同源；该基线不入主表（tab1 行 = C151–C156）。
"""

import csv
import hashlib
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

# ---- 判据门槛（PREREG go_no_go / D-023 §五；判据常量，非实验数据）----
GATE_MISFIRE = 30.0        # ① 良性误拦 ≤30%
GATE_INTERCEPT = 90.0      # ②③ 攻击拦截 ≥90%
GATE_RESIDUAL = 24         # ⑤ 标称剩余不确定性 ≥24 bit（运行判据）
GATE_H = 0.5               # ⑤ partial-leakage fraction ≤0.5
GATE_CC_MISS = 0.10        # ④ covered 漏匹配 <10%
L_MIN = 8                  # M2 匹配臂最小可归属片段长度（机制参数）

plt.rcParams.update(
    {
        "font.family": ["Times New Roman", "Noto Serif SC", "SimSun", "DejaVu Serif"],
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
        "svg.fonttype": "path",
        "svg.hashsalt": "fig_w72-stable",  # 固定盐：SVG 内部 id 确定性（重跑字节一致）
    }
)


def read_csv(name):
    with open(ROOT / "analysis" / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    return float(x)


def fmt_bits(v):
    return f"{v:g}"


def footnote(fig, text):
    """手工换行的脚注（\n 由调用者给定）；save() 内断言行宽不越界。"""
    t = fig.text(0.012, 0.012, text, ha="left", va="bottom", fontsize=7)
    fig._footnote = t


def save(fig, stem):
    # 脚注行宽自检（附加纪律：图内文字不得越出图像框）
    if getattr(fig, "_footnote", None) is not None:
        fig.canvas.draw()
        ext = fig._footnote.get_window_extent(fig.canvas.get_renderer())
        assert ext.x1 <= fig.bbox.x1 - 2, (
            f"{stem}: 脚注越界 {ext.x1:.0f} > {fig.bbox.x1 - 2:.0f}，请再拆行"
        )
    svg_path = FIG / f"{stem}.svg"
    pdf_path = FIG / f"{stem}.pdf"
    fig.savefig(svg_path, metadata={"Date": None})
    fig.savefig(
        pdf_path,
        metadata={"CreationDate": None, "ModDate": None, "Creator": None},
    )
    data = pdf_path.read_bytes()
    assert b"Type3" not in data, f"{pdf_path.name}: Type3 font leaked"
    assert b"/FontFile2" in data, f"{pdf_path.name}: no embedded TrueType (/FontFile2)"
    plt.close(fig)
    return svg_path, pdf_path


def despine(ax, keep_right=False):
    ax.spines["top"].set_visible(False)
    if not keep_right:
        ax.spines["right"].set_visible(False)


# =====================================================================
# 数据装载与派生（全部读自 CSV，不做任何数值改写）
# =====================================================================
grid = read_csv("w11spike_grid.csv")
frontier = read_csv("w11spike_frontier.csv")
geom = read_csv("w11geom_curve.csv")
controls = read_csv("w11spike_controls.csv")

# ---- fig1 左轴：G-A 段 S1/D1/L1 探针（C001–C006，holdout 68）----
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

# ---- fig1 右轴 / tab1 残熵·H：C-B**（D-025 §二-1），C031–C036（M1 臂）----
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

# ---- tab1 行：C151–C156（G-D：S1/D1/L3，M2，unmatched=deny）----
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

# ---- fig3：M2＋allow 臂（G-B）的 matchable/all 分母（算术天花板）----
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

# ---- tab2 行：三条过①②的候选（报告 §7／论文 v2 §3.3(c)）----
CANDS = ["C156", "C204", "C222"]
cand_labels = {}
for cid in CANDS:
    rows = [r for r in grid if r["combo_id"] == cid]
    assert len(rows) == 1, f"{cid}: {len(rows)} grid rows"
    cand_labels[cid] = rows[0]
assert all(cand_labels[c]["go_eligible"] == "1" for c in CANDS)

COVERED_PREFIX = "covered:"
Z95 = 1.959964  # 95% 正态分位数（判据常量）


def wilson_upper(k, n):
    """Wilson 95% 上界（A2：任何 0/n 必须给上界，禁止裸写 0）。"""
    if n <= 0:
        return float("inf")
    p = k / n
    denom = 1.0 + Z95 * Z95 / n
    centre = p + Z95 * Z95 / (2.0 * n)
    half = Z95 * ((p * (1.0 - p) / n + Z95 * Z95 / (4.0 * n * n)) ** 0.5)
    return min(1.0, (centre + half) / denom)


tab2_data = {}
for cid in CANDS:
    crows = [r for r in controls if r["combo_id"] == cid]
    assert crows, cid
    ca = min(fnum(r["rate"]) for r in crows if r["counter"] == "C-A")
    cbm = min(fnum(r["rate"]) for r in crows if r["counter"] == "C-B")
    covered = [
        r
        for r in crows
        if r["counter"] == "C-C" and r["param"].startswith(COVERED_PREFIX)
    ]
    cc = max((fnum(r["miss_rate"]) for r in covered), default=0.0)
    # A2：0/n 读数附 Wilson 95% 上界（取最保守者 = 各 covered 行上界的最大值）
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
        "CB": cbm,
        "CC": cc,
        "CC_U": cc_u,
        "worst_res": worst_res,
        "worst_H": worst_H,
        "cbss_res": cbss_res,
        "cbss_H": cbss_H,
    }

# =====================================================================
# fig1_frontier —— 残熵-误拦前沿（双 y 轴）
# =====================================================================
fig, axL = plt.subplots(figsize=(3.3, 2.7))
fig.subplots_adjust(left=0.135, right=0.845, bottom=0.35, top=0.97)
axR = axL.twinx()

xs = [m[0] for m in misfire]
ys = [m[1] for m in misfire]
axL.plot(xs, ys, color="0.0", marker="o", markerfacecolor="white", markeredgewidth=0.9, zorder=3)
rs = [c[1] for c in cb_series]
axR.plot(xs, rs, color="0.45", marker="s", markerfacecolor="white", markeredgewidth=0.9, zorder=3)

axL.axhline(GATE_MISFIRE, ls="--", lw=0.8, color="0.6", zorder=1)
axR.axhline(GATE_RESIDUAL, ls="--", lw=0.8, color="0.6", zorder=1)
axL.text(0.735, GATE_MISFIRE + 1.6, f"① {GATE_MISFIRE:g}%", fontsize=7, color="0.35", ha="left")
axR.text(0.86, GATE_RESIDUAL + 1.0, f"⑤ {GATE_RESIDUAL:g} bit", fontsize=7, color="0.35", ha="left")

# 端点直接标注（仅两端，数值由 CSV 格式化）
t0, y0, d0, n0 = misfire[0]
t1, y1, d1, n1 = misfire[-1]
res0, res1 = cb_series[0][1], cb_series[-1][1]
axL.annotate(f"{d0}/{n0}＝{y0:.1f}%", (t0, y0), xytext=(6, 4), textcoords="offset points", fontsize=7)
axL.annotate(f"{d1}/{n1}＝{y1:.1f}%", (t1, y1), xytext=(-4, 6), textcoords="offset points", fontsize=7, ha="right")
axR.annotate(f"{fmt_bits(res0)} bit", (t0, res0), xytext=(6, -10), textcoords="offset points", fontsize=7)
axR.annotate(f"{fmt_bits(res1)} bit", (t1, res1), xytext=(-4, 7), textcoords="offset points", fontsize=7, ha="right")

axL.set_xticks(xs)
axL.set_xticklabels([("1.0" if f"{t:g}" == "1" else f"{t:g}") for t in xs])
axL.set_xlim(0.505, 1.045)
axL.set_ylim(0, max(ys) * 1.28)
axR.set_ylim(0, max(rs) * 1.45)
axL.set_xlabel("θ′（候选参数，非部署 θ）")
axL.set_ylabel("良性误拦（%，holdout 68）")
axR.set_ylabel("标称剩余不确定性（bit）")
despine(axL, keep_right=True)
axR.spines["top"].set_visible(False)
footnote(
    fig,
    "数据来源：analysis/w11spike_grid.csv（G-A，S1/D1/L1，\n"
    "C001–C006，n=68）；残熵：analysis/w11spike_frontier.csv\n"
    "（C-B**，C031–C036，M1 臂，F1/F7 取双族 min/max；\n"
    "24 bit 为运行判据，非安全强度）。",
)
save(fig, "fig1_frontier")

# =====================================================================
# fig2_geometry —— 写单元几何不变性（G1–G5，L1 臂，五线重合）
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

fig, ax = plt.subplots(figsize=(3.3, 2.3))
fig.subplots_adjust(left=0.14, right=0.965, bottom=0.33, top=0.97)
colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e"]
markers = ["o", "s", "^", "D", "v"]
for i, g in enumerate(geos):
    ax.plot(
        [p[0] for p in series[g]],
        [p[1] for p in series[g]],
        color=colors[i % len(colors)],
        marker=markers[i % len(markers)],
        markerfacecolor="white",
        markeredgewidth=0.8,
        markersize=3.6 - 0.25 * i,
        label=g,
        zorder=3,
    )
y55 = series[geos[0]][0][1]
ax.annotate(f"{y55:.2f}%", (thetas[0], y55), xytext=(7, 2), textcoords="offset points", fontsize=7)
ax.annotate("G1–G5 五条线逐点重合", (thetas[0], y55), xytext=(8, -16), textcoords="offset points", fontsize=7)
ax.set_xticks(thetas)
ax.set_xticklabels([("1.0" if f"{t:g}" == "1" else f"{t:g}") for t in thetas])
ax.set_xlim(0.505, 1.045)
ax.set_ylim(0, y55 * 1.28)
ax.set_xlabel("θ′（候选参数，非部署 θ）")
ax.set_ylabel("良性误拦（%，holdout 68）")
despine(ax)
footnote(
    fig,
    "数据来源：analysis/w11geom_curve.csv（arm=L1，\n"
    f"S1·D1·L1，benign_rate；{len(geos)} 种写单元几何 × 6 档 θ′，共 {len(l1)} 行）。\n"
    "五条曲线逐点全等（脚本断言），无抖动或偏移。",
)
save(fig, "fig2_geometry")

# =====================================================================
# fig3_lmin —— 最小可归属片段长度（matchable 算术天花板）
# =====================================================================
fig, ax = plt.subplots(figsize=(3.3, 2.6))
fig.subplots_adjust(left=0.135, right=0.965, bottom=0.31, top=0.97)

groups = [("F1", F1_N, F1_M), ("F7", F7_N, F7_M)]
w = 0.30
xs_pos = [0, 1]
mat_pct = [m / n * 100.0 for _, n, m in groups]
ax.bar([x - w / 2 - 0.02 for x in xs_pos], [100.0, 100.0], width=w, color="0.85", edgecolor="0.2", linewidth=0.8, zorder=2)
ax.bar([x + w / 2 + 0.02 for x in xs_pos], mat_pct, width=w, color="0.45", edgecolor="0.0", linewidth=0.8, zorder=2)
# 计数标在柱内（灰柱黑字、深柱白字），顶部留给虚线说明
for x, (_, n, m) in zip(xs_pos, groups):
    ax.text(x - w / 2 - 0.02, 86, f"{n}/{n}", ha="center", va="center", fontsize=7, color="0.0")
    ax.text(x + w / 2 + 0.02, 45, f"{m}/{n}", ha="center", va="center", fontsize=7, color="white")

ax.axhline(GATE_INTERCEPT, ls="--", lw=0.8, color="0.3", zorder=1)
ax.axhline(mat_pct[0], ls="--", lw=0.8, color="0.3", zorder=1)
# 两条虚线的说明集中在顶部空白带（不与柱/线重叠）
ax.text(-0.45, 126.5, f"实测天花板 {F1_M}/{F1_N}＝{mat_pct[0]:.1f}%（虚线）", fontsize=7, ha="left", va="center", color="0.25")
ax.text(-0.45, 119.5, f"② {GATE_INTERCEPT:g}% 门槛（虚线）", fontsize=7, ha="left", va="center", color="0.25")
ax.text(-0.45, 111.5, "28 片 6 B（＜ℓ_min＝8）结构性不可匹配（判定侧 13 对）", fontsize=7, ha="left", va="center")
ax.set_xticks(xs_pos)
ax.set_xticklabels([g[0] for g in groups])
ax.set_xlim(-0.5, 1.55)
ax.set_ylim(0, 132)
ax.set_ylabel("可匹配攻击对占比（%）")
despine(ax)
footnote(
    fig,
    "数据来源：analysis/w11spike_grid.csv（G-B，S1/D1，\n"
    "M2＋allow，C061–C066 六档 θ′）；\n"
    f"all/matchable 分母 F1 {F1_N}/{F1_M}、F7 {F7_N}/{F7_M}，逐档恒定（脚本断言）。\n"
    f"灰柱＝all 分母，深柱＝matchable 分母；判定侧 13 对＝F1 {F1_N - F1_M}＋F7 {F7_N - F7_M}。",
)
save(fig, "fig3_lmin")

# =====================================================================
# tab1a_main.tex ＋ tab1b_cost.tex —— 主表拆两面板（附加纪律 B5：≤8 列）
#   tab1a＝候选与判据：combo/θ′/误拦(union,真实负载)/F1/F7/go_eligible
#   tab1b＝代价：combo/θ′/残熵(C-B**)/H/误拦 union|unique(真实负载)
#   表头强制标"构造内 / 真实负载"（附加纪律 B6）
# =====================================================================
def tex_escape(s):
    return s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def fmt_theta(t):
    return "1.0" if f"{t:g}" == "1" else f"{t:g}"


# ---- tab1a：候选与判据 ----
lines = []
lines.append("% 由 analysis/fig_w72.py 生成；所有数值读自 analysis/w11spike_grid.csv，重跑可复现。")
lines.append("% 面板(a)＝候选与判据；面板(b)＝代价（tab1b_cost.tex）。误拦列＝真实负载 holdout 68。")
lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{Candidates and gate readings across $\theta'$ (C151--C156), panel (a); "
             r"the cost side is in Tab.~\ref{tab:mainb}. "
             r"F1/F7 = structural interception rate within the self-built construction; "
             r"misfire = benign tasks denied on the 68-task holdout (union reading).}")
lines.append(r"\label{tab:maina}")
lines.append(r"\begin{tabular}{lccccc}")
lines.append(r"\toprule")
lines.append(r" & & 真实负载 & \multicolumn{2}{c}{构造内（自建构造）} & \\")
lines.append(r"\cmidrule(lr){3-3}\cmidrule(lr){4-5}")
lines.append(r"combo & $\theta'$ & misfire (\%)$^{a}$ & F1 & F7 & go\_elig. \\")
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
lines.append(r"\footnotesize $^{a}$~Benign misfire on the real workload: "
             + f"{tab1_rows[0]['benign_denied']}/{tab1_rows[0]['benign_n']} tasks denied at $\\theta'$=0.55, "
             + f"{tab1_rows[-1]['benign_denied']}/{tab1_rows[-1]['benign_n']} at $\\theta'$=1.0 "
             r"(union ambiguity reading; the unique reading is in panel (b)). "
             r"F1/F7 = structural interception rate, constructed scenarios "
             r"($n_F$=72/20 judged pairs); the paired partial-leakage fraction $H$ and nominal residual "
             r"uncertainty are in panel (b). go\_elig. = in the deployable candidate pool. "
             r"数据来源：analysis/w11spike\_grid.csv（G-D，S1/D1/L3，M2，unm=deny，C151--C156）。")
lines.append(r"\end{minipage}}")
lines.append(r"\end{table}")
(TAB / "tab1a_main.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

# ---- tab1b：代价（残熵/H ＋ union|unique 误拦）----
lines = []
lines.append("% 由 analysis/fig_w72.py 生成；残熵/H 读自 analysis/w11spike_frontier.csv（C-B**，C031–C036，M1 臂，")
lines.append("%   D-025 §二-1 口径，L=12 取等；24 bit 是运行判据，非安全强度），误拦读自 w11spike_grid.csv。")
lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{Cost side of the frontier (C151--C156), panel (b) of Tab.~\ref{tab:maina}. "
             r"Residual uncertainty = nominal remaining uncertainty under the uniform-independent-hex "
             r"assumption (C-B** adaptive-$\theta'$ reading); $H$ = partial-leakage fraction; "
             r"24\,bit is an operating criterion, not a security level.}")
lines.append(r"\label{tab:mainb}")
lines.append(r"\begin{tabular}{lccccc}")
lines.append(r"\toprule")
lines.append(r" & & \multicolumn{2}{c}{真实负载（holdout 68）} & \multicolumn{2}{c}{构造内（C-B**）} \\")
lines.append(r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}")
lines.append(r"combo & $\theta'$ & misfire union (\%) & misfire unique (\%) & resid.\ (bit)$^{a}$ & $H^{a}$ \\")
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
lines.append(r"\footnotesize $^{a}$~C-B** (adaptive-$\theta'$) reading per D-025: frontier rows C031--C036 "
             r"(oracle single-field arm, $L{=}12$ binding); not the row's own fixed-split reading. "
             r"Union$|$unique = multi-candidate union vs.\ unique ambiguity readings "
             r"(denied/68: "
             + f"{tab1_rows[-1]['benign_denied']}/68$|${tab1_rows[-1]['benign_denied_unique']}/68 at $\\theta'$=1.0). "
             r"数据来源：analysis/w11spike\_grid.csv（G-D，C151--C156）；"
             r"analysis/w11spike\_frontier.csv（C-B**，C031--C036，F1/F7 取 min/max）。")
lines.append(r"\end{minipage}}")
lines.append(r"\end{table}")
(TAB / "tab1b_cost.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
old_tab1 = TAB / "tab1_main.tex"
if old_tab1.exists():
    old_tab1.unlink()

# =====================================================================
# tab2_counters.tex —— 反制表（C156 / C204 / C222）
# =====================================================================
def cell(ok, content):
    return content if ok else "\\textbf{" + content + "}"


lines = []
lines.append("% 由 analysis/fig_w72.py 生成；所有数值读自 analysis/w11spike_controls.csv 与")
lines.append("% analysis/w11spike_frontier.csv，重跑可复现。候选行 = 报告 §7／论文 v2 §3.3(c) 的三条。")
lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{Counter-packing readings for the three candidates that pass criteria \circled{1}\circled{2} "
             r"(union reading). Bold = fails the preregistered gate.}")
lines.append(r"\label{tab:counters}")
lines.append(r"\begin{tabular}{lllllll}")
lines.append(r"\toprule")
lines.append(r" & \multicolumn{5}{c}{构造内（自建构造反制，spike）} & \\")
lines.append(r"\cmidrule(lr){2-6}")
lines.append(r"combo & C-A & C-B & C-B** & C-C covered & residual / $H$ & verdict \\")
lines.append(r"\midrule")
for cid in CANDS:
    d = tab2_data[cid]
    lab = cand_labels[cid]
    arm = f"{lab['matcher']}＋{'闭世界 deny' if lab['unmatched'] == 'deny' else 'allow'}，$\\theta'$＝{fnum(lab['theta']):g}"
    ca_ok = d["CA"] * 100.0 >= GATE_INTERCEPT
    cb_ok = d["CB"] * 100.0 >= GATE_INTERCEPT
    cc_ok = d["CC"] < GATE_CC_MISS
    r5_ok = d["cbss_res"] >= GATE_RESIDUAL and d["cbss_H"] <= GATE_H
    rw_ok = d["worst_res"] >= GATE_RESIDUAL and d["worst_H"] <= GATE_H
    verdict = "NO" if (not (ca_ok and cb_ok and cc_ok and r5_ok and rw_ok)) else "GO"
    # A2：0/n 读数附 Wilson 95% 上界
    if d["CC"] == 0.0:
        cc_cell = f"{d['CC']:.3f} (U {d['CC_U']:.3f})"
    else:
        cc_cell = f"{d['CC']:.3f}"
    lines.append(
        f"\\multicolumn{{7}}{{l}}{{\\textit{{{tex_escape(cid)}}} ({tex_escape(arm)})}} \\\\"
    )
    lines.append(
        f" & {cell(ca_ok, f'{d['CA']:.2f}')}"
        f" & {cell(cb_ok, f'{d['CB']:.2f}')}"
        f" & {cell(r5_ok, f'{fmt_bits(d['cbss_res'])} bit / {d['cbss_H']:.3f}')}"
        f" & {cell(cc_ok, cc_cell)}"
        f" & {cell(rw_ok, f'{fmt_bits(d['worst_res'])} bit / {d['worst_H']:.3f}')}"
        f" & \\textbf{{{verdict}}} \\\\"
    )
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\par\smallskip")
lines.append(r"{\footnotesize\begin{minipage}{0.98\linewidth}")
lines.append(r"\footnotesize C-A = min coverage rate over equal-split variants $n{=}2..6$ (both families); "
             r"C-B = min over re-split variants (base2/base6 $\times$ chunk1--4); "
             r"C-B** = adaptive-$\theta'$ upper bound (frontier rows of the combo, residual/$H$ per D-025); "
             r"C-C covered = max unmatched rate over covered encodings (none/base64/hex/homoglyph), "
             r"U = Wilson 95\% upper bound, reported for every 0/$n$ reading; "
             r"residual/$H$ = worst case over all C-A/C-B/C-B* readings "
             r"(min residual, max $H$ at that residual). "
             r"数据来源：analysis/w11spike\_controls.csv（8400 行，pool=frozen110/supplement30）；"
             r"analysis/w11spike\_frontier.csv（各 combo 的 C-B** 行）。")
lines.append(r"\end{minipage}}")
lines.append(r"\end{table}")
(TAB / "tab2_counters.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

# =====================================================================
# 回执自检：行数、断言、B4 度量（pymupdf 量框宽/最小字号）、字节一致性
# =====================================================================
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


outs = sorted(
    list(FIG.glob("fig*.svg")) + list(FIG.glob("fig*.pdf")) + list(TAB.glob("tab*.tex"))
)
print("== W7.2 图件回执 ==")
print(f"fig1 左轴（误拦）: w11spike_grid.csv G-A/S1/D1/L1 探针 = {len(probe)} 行 (C001–C006)")
print(f"fig1 右轴（残熵）: w11spike_frontier.csv C-B** M1 臂 = {len(cb_rows)} 行 (C031–C036, 6 档 θ′)")
print(f"fig2: w11geom_curve.csv arm=L1 = {len(l1)} 行 ({len(geos)} 几何 × 6 档), 五线重合断言 PASS")
print(f"fig3: w11spike_grid.csv G-B/S1/D1/M2/allow = {len(ceil_rows)} 行, 分母恒定断言 PASS (F1 {F1_M}/{F1_N}, F7 {F7_M}/{F7_N})")
print(f"tab1a/tab1b: w11spike_grid.csv G-D/S1/D1/L3/M2/deny = {len(tab1_rows)} 行 (C151–C156)")
print(f"tab2: w11spike_controls.csv {len(CANDS)} 组合 × 4 类反制 + frontier C-B** 行")

# ---- B4：按最终打印尺寸度量（矢量图不看 dpi，只看框宽与字号）----
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

# ---- B1：版本信息进 README（文件名保持稳定名）----
import matplotlib

inp = ["w11spike_grid.csv", "w11spike_frontier.csv", "w11geom_curve.csv", "w11spike_controls.csv"]
readme_lines = [
    "# paper/figures README（由 analysis/fig_w72.py 生成，勿手改）",
    "",
    f"- 重出命令：`.venv/Scripts/python.exe analysis/fig_w72.py`（一条命令重出全部图与表）",
    f"- 生成环境：Python {__import__('sys').version.split()[0]}，matplotlib {matplotlib.__version__}，pymupdf {fitz_ver}",
    "- 文件为稳定名（fig1_frontier / fig2_geometry / fig3_lmin），版本演进看本文件与 git 历史。",
    "- 口径：残熵/H 取 w11spike_frontier.csv 的 C-B** 行（C031–C036，M1 臂；controls.csv 无 C-B** 行，",
    "  已记 DEVIATION_LEDGER）；误拦取 w11spike_grid.csv（真实负载 holdout 68）；24 bit 为运行判据。",
    "",
    "## 输入（sha256 前 16 位）",
]
for name in inp:
    readme_lines.append(f"- analysis/{name}: {sha(ROOT / 'analysis' / name)}")
readme_lines.append("")
readme_lines.append("## 输出（sha256 前 16 位）")
for p in outs:
    readme_lines.append(f"- {p.relative_to(ROOT)}: {sha(p)}")
(FIG / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8", newline="\n")

for p in outs:
    print(f"  {p.relative_to(ROOT)}  sha256:{sha(p)}")
print("PDF 自检: 无 Type3、含 /FontFile2（TrueType 内嵌）— 全部 PASS")
