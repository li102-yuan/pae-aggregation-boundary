# -*- coding: utf-8 -*-
"""run_geom.py — `W11.4` 几何扫掠执行器（90 行 ＝ 5 档 × 6 个 θ′ × 3 臂）。

入口断言（顺序即纪律，任一不过即 `SpikeStop`）：
  1. 零模型调用：`GUARD.install()` ＋ `assert_no_model_imports()`；
  2. `check_freeze()`：`FREEZE_GEOM.sha256` 三件 `OK`（**冻结早于第一个候选**）；
  3. `grid_geom.json` 恰 90 行、(档, θ′, 臂) 组合完备、id 唯一；
  4. `G1` 重切世界与 `W11.SPIKE` 良性世界**逐 episode 逐字节相同**（回归锚点前提）。

判定（`PREREG_GEOM.json` 写死，本文件只是执行）：
  * `H1_失效`：若 `G2` 或 `G3` 在 θ′=0.55 时 ① ≤30%（**任一臂**取最小值）；
  * `H1_成立`：否则若 `G3` 在 θ′=0.55 时 ① 仍 >30%（**三臂全 >30%**）；
  * 两者同时成立时**以失效优先**（`G2` 已穿过即说明空可行域依赖写几何），
    边界点记首个 ≤30% 的档位；公式与优先级都在预注册里，不在此处改。

用法：
  python -m src.spike.w11geom.run_geom             # 90 行 + 图 + checks
"""
from __future__ import annotations

import argparse

from src.gate.history import _covered_bytes, _merge
from src.spike.w11_matching import common, data, gate, matching
from src.spike.w11geom import recut

GEOM_CONFIGS = common.ROOT / "configs" / "w11geom"
FREEZE_NAMES = ("PREREG_GEOM.json", "grid_geom.json", "inputs.json")
FREEZE_NAME = "FREEZE_GEOM.sha256"
THRESHOLD = 0.30
EXPECT_ROWS = 90
PROBE_EXPECT = {"0.55": 38, "0.7": 35, "0.8": 23, "0.9": 23, "0.95": 23, "1.0": 11}
# `W11.SPIKE` 的冻结网格（`analysis/w11spike_grid.csv`）——G1 的 L3 臂锚点
GRID_EXPECT = {("M2+deny", "0.55"): 39, ("M2+deny", "1.0"): 11,
               ("M2-short+deny", "0.55"): 39, ("M2-short+deny", "1.0"): 11}

FIELDS = ["geometry", "theta", "arm", "arm_label", "benign_n", "benign_denied",
          "benign_rate", "wilson_lo", "wilson_hi", "ambiguous_benign",
          "calls_total", "fragments_total", "deny_at_mean", "first_deny_cov_mean",
          "episodes_deny_unmatched", "episodes_deny_coverage",
          "matched_fragments", "pieces_lt8"]


def load_json(path):
    return common.load_json(path)


def check_freeze():
    rep = common.report_freeze(FREEZE_NAMES, out_dir=GEOM_CONFIGS, freeze_name=FREEZE_NAME)
    if rep["status"] != "OK":
        raise common.SpikeStop(
            f"冻结不一致（{rep['status']}）：{'; '.join(rep['diff']) or rep['freeze']}")
    return rep


def load_spec():
    prereg = load_json(GEOM_CONFIGS / "PREREG_GEOM.json")
    grid = load_json(GEOM_CONFIGS / "grid_geom.json")
    arms = {a["id"]: a for a in prereg["arms"]}
    thetas = [str(t) for t in prereg["thetas"]]
    geoms = {g["id"]: g for g in prereg["geometries"]}

    if tuple(geoms) != recut.GEOM_ORDER:
        raise common.SpikeStop(f"档位顺序与实现不一致：{tuple(geoms)}")
    for name, spec in recut.GEOM.items():
        got = geoms[name]
        if (got["kind"], got.get("ratio"), got.get("unit")) != \
                (spec["kind"], spec.get("ratio"), spec.get("unit")):
            raise common.SpikeStop(f"{name} 的粒度定义与实现不一致")

    rows = grid["rows"]
    if len(rows) != EXPECT_ROWS:
        raise common.SpikeStop(f"网格行数 {len(rows)} != {EXPECT_ROWS}")
    seen = set()
    for row in rows:
        key = (row["geometry"], str(row["theta"]), row["arm"])
        if key in seen:
            raise common.SpikeStop(f"重复组合：{key}")
        seen.add(key)
        if row["geometry"] not in geoms or row["arm"] not in arms \
                or str(row["theta"]) not in thetas:
            raise common.SpikeStop(f"越界组合：{key}")
    expect = {(g, t, a) for g in geoms for t in thetas for a in arms}
    if seen != expect:
        raise common.SpikeStop(f"组合不完备：缺 {sorted(expect - seen)[:3]}")
    if grid.get("rows") and len(grid["rows"]) != grid.get("count", EXPECT_ROWS):
        raise common.SpikeStop("grid 的 count 与实际行数不一致")
    return prereg, arms, thetas, rows


def matcher_for(arm, world, cache):
    key = (arm["matcher"], arm["norm"], world.name.split("/")[0])
    if key not in cache:
        cache[key] = (None if arm["matcher"] in (None, "none")
                      else matching.build(arm["matcher"], world.field_text, norm=arm["norm"]))
    return cache[key]


def run_row(row, arms, world, field_len, cap, cache):
    arm = arms[row["arm"]]
    rule = gate.Rule(scope=arm["scope"], denom=arm["denom"], lineage=arm["lineage"],
                     theta=float(row["theta"]), matcher=arm["matcher"], norm=arm["norm"],
                     unmatched=arm["unmatched"], dest=arm["dest"])
    matcher = matcher_for(arm, world, cache)
    holdout = [e for e in world.episodes if e.split == "holdout"]
    results = [gate.replay(e, rule, matcher, field_len, cap) for e in holdout]

    denied = sum(1 for r in results if r.deny_any)
    lo, hi = gate.wilson(denied, len(holdout))
    first_cov = [r.calls[r.deny_at - 1].coverage for r in results if r.deny_any]
    deny_at = [r.deny_at for r in results if r.deny_any]
    reasons = [r.deny_reasons[0] for r in results if r.deny_any]
    lens = [f.length for e in holdout for c in e.calls for f in c]
    return {
        "geometry": row["geometry"], "theta": str(row["theta"]), "arm": row["arm"],
        "arm_label": arm["label"],
        "benign_n": len(holdout), "benign_denied": denied,
        "benign_rate": round(denied / len(holdout), 6),
        "wilson_lo": round(lo, 6), "wilson_hi": round(hi, 6),
        "ambiguous_benign": sum(r.ambiguous_fragments for r in results),
        "calls_total": sum(len(e.calls) for e in holdout),
        "fragments_total": sum(r.total_fragments for r in results),
        "deny_at_mean": round(sum(deny_at) / len(deny_at), 3) if deny_at else None,
        "first_deny_cov_mean": round(sum(first_cov) / len(first_cov), 6) if first_cov else None,
        "episodes_deny_unmatched": sum(1 for x in reasons if x == "unmatched_content"),
        "episodes_deny_coverage": sum(1 for x in reasons if x == "coverage_threshold"),
        "matched_fragments": sum(r.matched_fragments for r in results),
        "pieces_lt8": sum(1 for n in lens if n < 8),
    }


def by_key(rows):
    return {(r["geometry"], str(r["theta"]), r["arm"]): r for r in rows}


def judge(rows):
    """按 `PREREG_GEOM.json` 的 `decision_rule` 写死执行；**不改阈值、不改档位**。"""
    at = by_key(rows)
    arms = sorted({r["arm"] for r in rows})
    rate_min = {(g, t): min(at[(g, t, a)]["benign_rate"] for a in arms)
                for (g, t, _a) in at}

    def r(g):
        return rate_min[(g, "0.55")]

    boundary = next((g for g in recut.GEOM_ORDER if r(g) <= THRESHOLD), None)
    fails = any(r(g) <= THRESHOLD for g in ("G2", "G3"))
    holds = r("G3") > THRESHOLD
    if fails:
        verdict = "H1_FAILS"
    elif holds:
        verdict = "H1_HOLDS"
    else:
        verdict = "UNDECIDED"
    if fails and holds:
        note = "两条件同时触发：按预注册『失效优先』取 H1_FAILS"
    elif fails:
        note = "G2/G3 中已有档位在 θ′=0.55 时 ≤30%"
    elif holds:
        note = "G1–G5 全档在 θ′=0.55 时均 >30%"
    else:
        note = "G3 ≤30% 但 G2 >30%，且未触发失效条件——中间区间，交负责人"
    return {"verdict": verdict, "boundary_geometry_at_0.55": boundary,
            "rate_min_at_0.55": {g: round(r(g), 6) for g in recut.GEOM_ORDER},
            "rate_min_by_arm": {a: round(at[("G3", "0.55", a)]["benign_rate"], 6) for a in arms},
            "rule": "min over arms; 失效优先", "note": note,
            "threshold": THRESHOLD}


def final_coverage(world):
    """每任务终态覆盖（＝该任务合法写入占字段的比例，重切不变）。"""
    out = []
    for ep in [e for e in world.episodes if e.split == "holdout"]:
        spans = {}
        for call in ep.calls:
            for frag in call:
                spans.setdefault(frag.key(), []).append((frag.offset, frag.offset + frag.length))
        cov = {k: _covered_bytes(_merge(v), world.field_len[k]) / world.field_len[k]
               for k, v in spans.items()}
        key = max(cov, key=lambda k: (cov[k], k))
        out.append({"task_id": ep.task_id, "cell": f"{key[0]}.{key[1]}",
                    "field_len": world.field_len[key],
                    "bytes_written": sum(f.length for c in ep.calls for f in c),
                    "final_coverage": round(cov[key], 6),
                    "calls": len(ep.calls)})
    return out


def analytic(theta_rows):
    """解析穿越点：①(θ′) = #{任务: 终态覆盖 ≥ θ′}。给出 ①≤30% 所需的 θ′ 下界（开区间）。"""
    covs = sorted((r["final_coverage"] for r in theta_rows), reverse=True)
    n = len(covs)
    k_max = int(n * THRESHOLD)                     # 68 × 0.30 = 20
    if k_max >= n:
        return {"n": n, "k_allow": k_max, "theta_star_exclusive": None}
    return {"n": n, "k_allow": k_max,
            "theta_star_exclusive": covs[k_max],
            "meaning": f"①(θ′) ≤ 30% ⇔ θ′ > {covs[k_max]}（第 {k_max + 1} 大终态覆盖）"}


# ---------------------------------------------------------------- 图
COLORS = {"G1": "#1f3b73", "G2": "#2e86ab", "G3": "#2f7d4f",
          "G4": "#b8791f", "G5": "#9b3b3b"}
DASH = {"G1": "", "G2": "7 4", "G3": "2 3", "G4": "10 4 2 4", "G5": "3 5"}


def _panel(rows, arm_id, arm_label, left, top, w, h, thetas):
    x0, x1 = left + 52, left + w - 16
    y0, y1 = top + 16, top + h - 74
    tmin, tmax = float(thetas[0]), float(thetas[-1])

    def px(t):
        return x0 + (float(t) - tmin) / (tmax - tmin) * (x1 - x0)

    def py(v):
        return y1 - v * (y1 - y0)

    out = [f'<rect x="{left}" y="{top}" width="{w}" height="{h}" rx="6" fill="#ffffff" '
           f'stroke="#d8dde5"/>']
    out.append(f'<text x="{left + 12}" y="{top + 22}" font-size="12.5" font-weight="700" '
               f'fill="#1b2430">{arm_label}</text>')
    for v in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = py(v)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                   f'stroke="{"#c9ced6" if v in (0.0, 1.0) else "#eceff3"}"/>')
        out.append(f'<text x="{x0 - 8}" y="{y + 3.5:.1f}" font-size="9.5" fill="#5b6673" '
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
    out.append(f'<text x="{x1 - 2}" y="{y30 - 5:.1f}" font-size="9" fill="#b03a2e" '
               f'text-anchor="end">30%</text>')

    sub = [r for r in rows if r["arm"] == arm_id]
    for g in reversed(recut.GEOM_ORDER):
        pts = sorted((r for r in sub if r["geometry"] == g), key=lambda r: float(r["theta"]))
        if not pts:
            continue
        d = " ".join(f'{"M" if i == 0 else "L"}{px(r["theta"]):.1f},{py(r["benign_rate"]):.1f}'
                     for i, r in enumerate(pts))
        dash = f' stroke-dasharray="{DASH[g]}"' if DASH[g] else ""
        width = "3.4" if g == "G1" else "2.2"
        out.append(f'<path d="{d}" fill="none" stroke="{COLORS[g]}" stroke-width="{width}"'
                   f'{dash} stroke-linejoin="round"/>')
        for r in pts:
            out.append(f'<circle cx="{px(r["theta"]):.1f}" cy="{py(r["benign_rate"]):.1f}" '
                       f'r="2.4" fill="{COLORS[g]}"/>')

    cross = None
    for r in sorted(sub, key=lambda r: float(r["theta"])):
        if r["benign_rate"] <= THRESHOLD:
            cross = r
            break
    if cross is not None:
        cx, cy = px(cross["theta"]), py(cross["benign_rate"])
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="none" stroke="#b03a2e" '
                   f'stroke-width="1.6"/>')
        out.append(f'<text x="{cx - 10:.1f}" y="{cy - 9:.1f}" font-size="9.5" fill="#b03a2e" '
                   f'text-anchor="end">{cross["geometry"]} 首次 ≤30%（θ′={cross["theta"]}）</text>')

    at55 = next(r for r in sub if r["geometry"] == "G1" and str(r["theta"]) == "0.55")
    out.append(f'<text x="{x0 + 4}" y="{y0 + 12}" font-size="9.5" fill="#3c4653">'
               f'θ′=0.55 时 G1 ＝ {at55["benign_denied"]}/68 ＝ '
               f'{at55["benign_rate"] * 100:.1f}%</text>')

    lx = left + 12
    for g in recut.GEOM_ORDER:
        dash = f' stroke-dasharray="{DASH[g]}"' if DASH[g] else ""
        out.append(f'<line x1="{lx}" y1="{top + h - 22}" x2="{lx + 16}" y2="{top + h - 22}" '
                   f'stroke="{COLORS[g]}" stroke-width="{3 if g == "G1" else 2}"{dash}/>')
        out.append(f'<text x="{lx + 20}" y="{top + h - 18}" font-size="9.5" fill="#3c4653">'
                   f'{g}</text>')
        lx += 56
    return "".join(out)


def plot(rows, path, thetas):
    arms = [("L1", "L1 基线（S1·D1·L1）"),
            ("M2+deny", "S1·D1·L3·M2·deny"),
            ("M2-short+deny", "S1·D1·L3·M2-short·deny")]
    W, H, pw, ph, gap, left, top = 1240, 470, 372, 330, 18, 22, 58
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="Microsoft YaHei, SimHei, Noto Sans CJK SC, '
             f'sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#f7f9fb"/>',
             f'<text x="{left}" y="30" font-size="15" font-weight="700" fill="#16202b">'
             f'W11.4 几何扫掠：良性误拦 vs θ′（5 档写单元 × 3 臂；holdout 68 任务）</text>',
             f'<text x="{left}" y="48" font-size="10.5" fill="#5b6673">'
             f'写单元 ＝ 字段长 × 比例（G5 为绝对 3 B 上限）；总字节逐任务守恒；'
             f'误拦 ＝ episode 内至少一次 deny 的任务数 / 68</text>']
    for i, (arm_id, label) in enumerate(arms):
        parts.append(_panel(rows, arm_id, label, left + i * (pw + gap), top, pw, ph, thetas))
    parts.append(f'<text x="{left}" y="{H - 8}" font-size="9.5" fill="#7a8494">'
                 f'L1 面板五线逐点重合是结构性结果（不变性引理：终态覆盖与切分无关）；'
                 f'M2 面板的抬升来自 ℓ_min=8 边界（&lt;8 B 的碎片无法归属 ⇒ unmatched=deny）。'
                 f'数据：analysis/w11geom_curve.csv</text>')
    parts.append("</svg>")
    common.write_text(path, "\n".join(parts) + "\n")
    return path


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="analysis/w11geom_curve.csv")
    ap.add_argument("--checks-out", default="analysis/w11geom_checks.json")
    ap.add_argument("--geometry-out", default="analysis/w11geom_geometry.csv")
    ap.add_argument("--invariance-out", default="analysis/w11geom_invariance.csv")
    ap.add_argument("--fig", default="analysis/w11geom_curve.svg")
    args = ap.parse_args()

    common.GUARD.install()
    common.assert_no_model_imports()
    freeze = check_freeze()
    prereg, arms, thetas, grid = load_spec()

    ben = data.load_benign()
    if sum(1 for e in ben.episodes if e.split == "holdout") != 68:
        raise common.SpikeStop("holdout 可写任务数不是 68")

    worlds, stats = {}, []
    for g in recut.GEOM_ORDER:
        world, st = recut.recut_world(ben, g)
        stats.append(st)
        worlds[g] = world

    # 回归锚点前提：G1 逐字节等于原世界
    g1_pairs = list(zip(ben.episodes, worlds["G1"].episodes))
    if any(len(a.calls) != len(b.calls) for a, b in g1_pairs):
        raise common.SpikeStop("G1 调用数与原世界不同")
    if any(f.content != g.content
           for a, b in g1_pairs for ca, cb in zip(a.calls, b.calls)
           for f, g in zip(ca, cb)):
        raise common.SpikeStop("G1 片段内容与原世界不同")

    cap = gate.entity_capacity(ben.field_len)
    cache, out = {}, []
    for i, row in enumerate(grid, 1):
        out.append(run_row(row, arms, worlds[row["geometry"]], ben.field_len, cap, cache))
        if i % 10 == 0 or i == len(grid):
            print(f"[{i}/{len(grid)}] {out[-1]['geometry']} θ′={out[-1]['theta']} "
                  f"{out[-1]['arm']} 误拦 {out[-1]['benign_denied']}/68", flush=True)

    common.write_csv(common.ROOT / args.out, out, FIELDS)

    # 诊断表：档位清单 + 逐任务终态覆盖
    geom_rows = [{k: v for k, v in st.items() if k != "conservation"} for st in stats]
    common.write_csv(common.ROOT / args.geometry_out, geom_rows,
                     ["geometry", "episodes", "fragments_in", "pieces_out", "split_fragments",
                      "calls_in", "calls_out", "bytes_total", "min_piece", "median_piece",
                      "max_piece", "pieces_lt8", "pieces_lt4"])
    cov = final_coverage(worlds["G1"])
    inv = []
    for r in cov:
        inv.append(r)
    for g in recut.GEOM_ORDER:
        cov_g = {x["task_id"]: x for x in final_coverage(worlds[g])}
        for r in inv:
            r[f"coverage_{g}"] = cov_g[r["task_id"]]["final_coverage"]
            r[f"calls_{g}"] = cov_g[r["task_id"]]["calls"]
    common.write_csv(common.ROOT / args.invariance_out, inv,
                     ["task_id", "cell", "field_len", "bytes_written", "final_coverage", "calls"]
                     + [f"coverage_{g}" for g in recut.GEOM_ORDER]
                     + [f"calls_{g}" for g in recut.GEOM_ORDER])

    at = by_key(out)
    l1 = {t: at[("G1", t, "L1")]["benign_denied"] for t in thetas}
    anchor_probe = {"expected": PROBE_EXPECT, "got": l1,
                    "match": all(int(l1[t]) == PROBE_EXPECT[t] for t in PROBE_EXPECT)}
    if not anchor_probe["match"]:
        raise common.SpikeStop(f"回归锚点破坏：L1 六档 {l1} != {PROBE_EXPECT}")

    anchor_l3 = {}
    for (arm, th), want in GRID_EXPECT.items():
        got = at[("G1", th, arm)]["benign_denied"]
        anchor_l3[f"{arm}@{th}"] = {"expected": want, "got": got, "match": got == want}
    if not all(v["match"] for v in anchor_l3.values()):
        raise common.SpikeStop(f"冻结核对失败：{anchor_l3}")

    # 不变性：L1 臂五档逐点相等；逐任务终态覆盖相等
    inv_ok = all(len({at[(g, t, "L1")]["benign_denied"] for g in recut.GEOM_ORDER}) == 1
                 for t in thetas)
    cov_ok = all(len({r[f"coverage_{g}"] for g in recut.GEOM_ORDER}) == 1 for r in inv)

    judgement = judge(out)
    verdict = judgement["verdict"]
    checks = {
        "rows": len(out), "expect_rows": EXPECT_ROWS,
        "freeze": {"status": freeze["status"], "lines": freeze["lines"],
                   "file": freeze["freeze"]},
        "guard": common.GUARD.report(),
        "geometry_stats": stats,
        "g1_identity": {"episodes": len(ben.episodes), "calls": sum(len(e.calls) for e in ben.episodes),
                        "match": True},
        "anchor_l1_probe": anchor_probe,
        "anchor_l3_grid": anchor_l3,
        "invariance_l1_rows_equal": inv_ok,
        "invariance_task_coverage_equal": cov_ok,
        "judgement": judgement,
        "analytic_crossing": analytic(cov),
        "monotone_violations": [
            {"arm": arm, "theta": th, "pair": [g1, g2],
             "from": at[(g1, th, arm)]["benign_denied"], "to": at[(g2, th, arm)]["benign_denied"]}
            for arm in sorted({r["arm"] for r in out})
            for th in thetas
            for g1, g2 in zip(recut.GEOM_ORDER, recut.GEOM_ORDER[1:])
            if at[(g2, th, arm)]["benign_denied"] < at[(g1, th, arm)]["benign_denied"]],
        "window": prereg["window"],
        "decision_ref": prereg["decision_ref"],
    }
    common.write_json(common.ROOT / args.checks_out, checks)
    plot(out, common.ROOT / args.fig, thetas)

    print(f"\n判定：{verdict} （{judgement['note']}）")
    print(f"θ′=0.55 各档最小误拦：{judgement['rate_min_at_0.55']}")
    print(f"边界点：{judgement['boundary_geometry_at_0.55']}")
    print(f"解析穿越点：{checks['analytic_crossing']}")
    print(f"L1 五档逐点相等：{inv_ok}；逐任务终态覆盖相等：{cov_ok}")
    print(f"落盘：{args.out}、{args.geometry_out}、{args.invariance_out}、{args.fig}、"
          f"{args.checks_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
