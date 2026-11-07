# -*- coding: utf-8 -*-
"""Figure generator for the write-granularity sweep."""
from __future__ import annotations

import argparse
import csv
import pathlib

from src.spike.w11_matching import common
from src.spike.w11geom import recut

THRESHOLD = 0.30
COLORS = {"G1": "#1f3b73", "G2": "#2e86ab", "G3": "#2f7d4f",
          "G4": "#b8791f", "G5": "#9b3b3b"}
DASH = {"G1": "", "G2": "7 4", "G3": "2 3", "G4": "10 4 2 4", "G5": "3 5"}
ARMS = [("L1", "L1 基线（S1·D1·L1）", "纯结构：① 的严格下界"),
        ("M2+deny", "S1·D1·L3·M2·deny", "ℓ_min=8：碎片 &lt;8 B 无法归属"),
        ("M2-short+deny", "S1·D1·L3·M2-short·deny", "ℓ_min=4：&lt;4 B 无法归属")]

W, H, PW, PH, GAP, LEFT, TOP = 1240, 500, 372, 356, 18, 22, 76


def load_rows(path):
    with pathlib.Path(path).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _panel(rows, arm_id, title, note, left, thetas, boxes):
    x0, x1 = left + 54, left + PW - 16
    y0, y1 = TOP + 50, TOP + PH - 86
    tmin, tmax = float(thetas[0]), float(thetas[-1])

    def px(t):
        return x0 + (float(t) - tmin) / (tmax - tmin) * (x1 - x0)

    def py(v):
        return y1 - float(v) * (y1 - y0)

    out = [f'<rect x="{left}" y="{TOP}" width="{PW}" height="{PH}" rx="7" fill="#ffffff" '
           f'stroke="#d8dde5"/>',
           f'<text x="{left + 14}" y="{TOP + 21}" font-size="12.5" font-weight="700" '
           f'fill="#16202b">{title}</text>',
           f'<text x="{left + 14}" y="{TOP + 36}" font-size="9.5" fill="#6b7684">{note}</text>']

    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = py(v)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                   f'stroke="{"#c9ced6" if v in (0.0, 1.0) else "#eef1f4"}"/>')
        out.append(f'<text x="{x0 - 8}" y="{y + 3.4:.1f}" font-size="9.5" fill="#5b6673" '
                   f'text-anchor="end">{int(v * 100)}%</text>')
    for t in thetas:
        out.append(f'<line x1="{px(t):.1f}" y1="{y1}" x2="{px(t):.1f}" y2="{y1 + 4}" '
                   f'stroke="#8b95a3"/>')
        out.append(f'<text x="{px(t):.1f}" y="{y1 + 16}" font-size="9.5" fill="#5b6673" '
                   f'text-anchor="middle">{t}</text>')
    out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{y1 + 31}" font-size="10.5" fill="#3c4653" '
               f'text-anchor="middle">θ′</text>')

    y30 = py(THRESHOLD)
    out.append(f'<line x1="{x0}" y1="{y30:.1f}" x2="{x1}" y2="{y30:.1f}" stroke="#b03a2e" '
               f'stroke-width="1.2" stroke-dasharray="6 3"/>')
    out.append(f'<text x="{x1 - 2}" y="{y30 - 6:.1f}" font-size="9" fill="#b03a2e" '
               f'text-anchor="end">30% 线</text>')

    sub = [r for r in rows if r["arm"] == arm_id]
    for g in recut.GEOM_ORDER:
        pts = sorted((r for r in sub if r["geometry"] == g), key=lambda r: float(r["theta"]))
        d = " ".join(f'{"M" if i == 0 else "L"}{px(r["theta"]):.1f},{py(r["benign_rate"]):.1f}'
                     for i, r in enumerate(pts))
        dash = f' stroke-dasharray="{DASH[g]}"' if DASH[g] else ""
        out.append(f'<path d="{d}" fill="none" stroke="{COLORS[g]}" stroke-width="2.4"'
                   f'{dash} stroke-linejoin="round"/>')
        for r in pts:
            cx, cy = px(r["theta"]), py(r["benign_rate"])
            boxes.append((left, cx, cy))
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" fill="{COLORS[g]}" '
                       f'stroke="#ffffff" stroke-width="0.6"/>')

    cross = next((r for r in sorted(sub, key=lambda r: float(r["theta"]))
                  if float(r["benign_rate"]) <= THRESHOLD), None)
    if cross is not None:
        cx, cy = px(cross["theta"]), py(cross["benign_rate"])
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="none" stroke="#b03a2e" '
                   f'stroke-width="1.5"/>')
        out.append(f'<text x="{cx - 12:.1f}" y="{cy + 3:.1f}" font-size="9.5" fill="#b03a2e" '
                   f'text-anchor="end">{cross["geometry"]} 首次 ≤30%（θ′={cross["theta"]}）'
                   f'</text>')

    lx = left + 14
    for g in recut.GEOM_ORDER:
        dash = f' stroke-dasharray="{DASH[g]}"' if DASH[g] else ""
        out.append(f'<line x1="{lx}" y1="{TOP + PH - 24}" x2="{lx + 18}" y2="{TOP + PH - 24}" '
                   f'stroke="{COLORS[g]}" stroke-width="2.4"{dash}/>')
        out.append(f'<text x="{lx + 23}" y="{TOP + PH - 20}" font-size="9.5" fill="#3c4653">'
                   f'{g}</text>')
        lx += 58
    return "".join(out)


def build(rows, thetas):
    boxes = []
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="Microsoft YaHei, SimHei, '
             f'Noto Sans CJK SC, sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#f7f9fb"/>',
             f'<text x="{LEFT}" y="32" font-size="15" font-weight="700" fill="#16202b">'
             f'W11.4 几何扫掠：良性误拦 vs θ′（5 档写单元 × 3 臂；holdout 68 个可写任务）</text>',
             f'<text x="{LEFT}" y="52" font-size="10.5" fill="#5b6673">'
             f'写单元 ＝ 字段长 × 比例（G5 为绝对 3 B 上限）；逐任务字节守恒；'
             f'误拦 ＝ episode 内至少一次 deny 的任务数 / 68；虚线 ＝ 30% 判定线</text>']
    for i, (arm_id, title, note) in enumerate(ARMS):
        left = LEFT + i * (PW + GAP)
        parts.append(_panel(rows, arm_id, title, note, left, thetas, boxes))
    parts.append(f'<text x="{LEFT}" y="{H - 30}" font-size="9.5" fill="#7a8494">'
                 f'L1 面板五条线逐点重合（55.9 / 51.5 / 33.8 / 33.8 / 33.8 / 16.2%），'
                 f'是结构性结果：S1/D1 下 ① 只取决于每任务终态覆盖，重切保并集 ⇒ 覆盖不变。</text>')
    parts.append(f'<text x="{LEFT}" y="{H - 14}" font-size="9.5" fill="#7a8494">'
                 f'M2／M2-short 面板的抬升来自 ℓ_min 边界（碎片无法归属 ⇒ unmatched=deny），'
                 f'不是覆盖变严；G5 全部碎片 &lt;4 B，故 68/68。</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n", boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="analysis/w11geom_curve.csv")
    ap.add_argument("--out", default="analysis/w11geom_curve.svg")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows = load_rows(common.ROOT / args.csv)
    thetas = sorted({str(r["theta"]) for r in rows}, key=float)
    svg, boxes = build(rows, thetas)

    y0, y1 = TOP + 50, TOP + PH - 86
    bad = [(left, cx, cy) for (left, cx, cy) in boxes
           if not (left + 54 - 1 <= cx <= left + PW - 16 + 1 and y0 - 1 <= cy <= y1 + 1)]
    if bad:
        raise common.SpikeStop(f"图元越界：{bad[:3]}（共 {len(bad)}）")
    if not args.check:
        common.write_text(common.ROOT / args.out, svg)
    print(f"图元 {len(boxes)} 个全部在绘图区内；{'只自检' if args.check else '落盘 ' + args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
