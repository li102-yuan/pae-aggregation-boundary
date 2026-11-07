# -*- coding: utf-8 -*-
"""Run the candidate grid and write per-row metrics with dual denominators and dual ambiguity readings."""
from __future__ import annotations

import argparse
import csv
import json
import pathlib

from src.spike.w11_matching import common, data, gate, matching

ENTROPY_BITS_PER_CHAR = 4.0          # state_store_v2.json 全为 hex（16 字符集）


class _UniqueOnly:
    """`unique` 口径的匹配器代理：多候选一律当未匹配（由上层 `unmatched` 策略处置）。"""

    def __init__(self, inner):
        self.inner = inner

    def locate(self, raw, declared):
        hits = self.inner.locate(raw, declared)
        return hits if len(hits) == 1 else []


def _matcher(name, norm, world, cache):
    key = (name, norm, world.name)
    if key not in cache:
        cache[key] = None if name in (None, "none") else matching.build(name, world.field_text, norm=norm)
    return cache[key]


def _wilson(k, n):
    lo, hi = gate.wilson(k, n)
    return round(lo, 6), round(hi, 6)


def _min_ell(matcher):
    if matcher is None:
        return None
    return min(getattr(matcher, "ells", matching.ELLS))


def _family(eps, rule, matcher, field_len, cap, min_ell):
    """→ (all 统计, matchable 统计, union 口径的 intercepted 计数)。"""
    results = [(ep, gate.replay(ep, rule, matcher, field_len, cap)) for ep in eps]
    hs = [r.delivered_truth_bytes / r.truth_len if r.truth_len else 1.0 for _e, r in results]
    bits = [ENTROPY_BITS_PER_CHAR * (r.truth_len - r.delivered_truth_bytes) for _e, r in results]
    all_stats = {
        "n": len(results),
        "intercepted": sum(1 for _e, r in results if r.intercepted),
        "H_mean": round(sum(hs) / len(hs), 6) if hs else None,
        "H_max": round(max(hs), 6) if hs else None,
        "residual_bits_min": round(min(bits), 2) if bits else None,
    }
    if min_ell is None:
        matchable = [(e, r) for e, r in results]
    else:
        matchable = [(e, r) for e, r in results
                     if all(f.length >= min_ell for c in e.calls for f in c)]
    m_hs = [r.delivered_truth_bytes / r.truth_len if r.truth_len else 1.0
            for _e, r in matchable]
    m_bits = [ENTROPY_BITS_PER_CHAR * (r.truth_len - r.delivered_truth_bytes)
              for _e, r in matchable]
    match_stats = {
        "n": len(matchable),
        "intercepted": sum(1 for _e, r in matchable if r.intercepted),
        "H_max": round(max(m_hs), 6) if m_hs else None,
        "residual_bits_min": round(min(m_bits), 2) if m_bits else None,
    }
    return all_stats, match_stats


def run_row(row, ben, mal, cap_b, cap_m, cache):
    rule = gate.Rule(scope=row["scope"], denom=row["denom"], lineage=row["lineage"],
                     theta=float(row["theta"]), matcher=row["matcher"], norm=row["norm"],
                     unmatched=row["unmatched"], dest=row["dest"])

    # ---- 良性：holdout 68（union 与 unique 两口径）----
    mb = _matcher(row["matcher"], row["norm"], ben, cache)
    mbu = _UniqueOnly(mb) if mb is not None else None
    holdout = [e for e in ben.episodes if e.split == "holdout"]
    denied = denied_u = amb_b = 0
    for ep in holdout:
        r = gate.replay(ep, rule, mb, ben.field_len, cap_b)
        denied += int(r.deny_any)
        amb_b += r.ambiguous_fragments
        if mbu is not None:
            denied_u += int(gate.replay(ep, rule, mbu, ben.field_len, cap_b).deny_any)
        else:
            denied_u += int(r.deny_any)
    lo, hi = _wilson(denied, len(holdout))

    # ---- 恶意：F1 72 / F7 20（dev 单列）----
    mm = _matcher(row["matcher"], row["norm"], mal, cache)
    mmu = _UniqueOnly(mm) if mm is not None else None
    min_ell = _min_ell(mm)
    per_fam, uni_fam, amb_m = {}, {}, 0
    for fam in ("F1", "F7"):
        eps = [e for e in mal.episodes if e.episode_id.startswith(fam + "/")]
        judged = [e for e in eps if e.split == "test"] if fam == "F7" else eps
        all_stats, match_stats = _family(judged, rule, mm, mal.field_len, cap_m, min_ell)
        per_fam[fam] = all_stats
        per_fam[fam].update({"match_n": match_stats["n"],
                             "match_intercepted": match_stats["intercepted"],
                             "match_residual_bits_min": match_stats["residual_bits_min"],
                             "match_H_max": match_stats["H_max"]})
        amb_m += sum(gate.replay(e, rule, mm, mal.field_len, cap_m).ambiguous_fragments
                     for e in judged)
        if mmu is not None:
            uni_fam[fam] = sum(1 for e in judged
                               if gate.replay(e, rule, mmu, mal.field_len, cap_m).intercepted)
        else:
            uni_fam[fam] = per_fam[fam]["intercepted"]

    def rate(k, n):
        return round(k / n, 6) if n else None

    return {
        "combo_id": row["combo_id"], "stage": row["stage"], "scope": row["scope"],
        "denom": row["denom"], "lineage": row["lineage"], "theta": row["theta"],
        "matcher": row["matcher"], "norm": row["norm"], "unmatched": row["unmatched"],
        "dest": row["dest"], "oracle": int(bool(row["oracle"])),
        "deployable": int(bool(row["deployable"])), "go_eligible": int(bool(row["go_eligible"])),
        "benign_n": len(holdout), "benign_denied": denied,
        "benign_rate": round(denied / len(holdout), 6), "wilson_lo": lo, "wilson_hi": hi,
        "benign_denied_unique": denied_u,
        "benign_rate_unique": round(denied_u / len(holdout), 6),
        "ambiguous_benign": amb_b, "ambiguous_malicious": amb_m,
        "F1_n": per_fam["F1"]["n"], "F1_intercepted": per_fam["F1"]["intercepted"],
        "F1_rate": rate(per_fam["F1"]["intercepted"], per_fam["F1"]["n"]),
        "F1_H_mean": per_fam["F1"]["H_mean"], "F1_H_max": per_fam["F1"]["H_max"],
        "F1_residual_bits_min": per_fam["F1"]["residual_bits_min"],
        "F1_match_n": per_fam["F1"]["match_n"],
        "F1_match_intercepted": per_fam["F1"]["match_intercepted"],
        "F1_rate_matchable": rate(per_fam["F1"]["match_intercepted"], per_fam["F1"]["match_n"]),
        "F1_match_residual_bits_min": per_fam["F1"]["match_residual_bits_min"],
        "F1_intercepted_unique": uni_fam["F1"],
        "F7_n": per_fam["F7"]["n"], "F7_intercepted": per_fam["F7"]["intercepted"],
        "F7_rate": rate(per_fam["F7"]["intercepted"], per_fam["F7"]["n"]),
        "F7_H_mean": per_fam["F7"]["H_mean"], "F7_H_max": per_fam["F7"]["H_max"],
        "F7_residual_bits_min": per_fam["F7"]["residual_bits_min"],
        "F7_match_n": per_fam["F7"]["match_n"],
        "F7_match_intercepted": per_fam["F7"]["match_intercepted"],
        "F7_rate_matchable": rate(per_fam["F7"]["match_intercepted"], per_fam["F7"]["match_n"]),
        "F7_match_residual_bits_min": per_fam["F7"]["match_residual_bits_min"],
        "F7_intercepted_unique": uni_fam["F7"],
    }


def check_clone_rows(out):
    """`G-G` 的 `allow`／`deny` 18 对必须读数全等（否则 234 列全等会被当成复制粘贴错）。"""
    gg = {}
    for row in out:
        if row["stage"] == "G-G":
            gg[(row["scope"], row["theta"])] = gg.get((row["scope"], row["theta"]), {})
            gg[(row["scope"], row["theta"])][row["unmatched"]] = row
    diffs = []
    # `*_unique` 是**诊断口径**（多候选当未匹配），`allow` 与 `deny` 对它的处置本就不同
    # （回落声明 vs 直接拒），故只对判定路径（union）断言逐列相等。
    skip = {"combo_id", "unmatched", "benign_denied_unique", "benign_rate_unique",
            "F1_intercepted_unique", "F7_intercepted_unique"}
    for key, pair in sorted(gg.items()):
        a, b = pair.get("allow"), pair.get("deny")
        if not a or not b:
            diffs.append({"pair": key, "why": "缺行"})
            continue
        bad = [k for k in a if k not in skip and a[k] != b[k]]
        if bad:
            diffs.append({"pair": key, "fields": bad})
    return {"pairs": len(gg), "mismatch": len(diffs), "detail": diffs[:5],
            "note": "M2-short 对全部片段命中 ⇒ unmatched=deny 永不触发 ⇒ 两行逐列相同"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=None, help="只跑某个 stage（如 G-A）；默认全量")
    ap.add_argument("--only", default=None, help="逗号分隔的 combo_id")
    ap.add_argument("--out", default="analysis/w11spike_grid.csv")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--checks-out", default="analysis/w11spike_grid_checks.json")
    args = ap.parse_args()

    common.GUARD.install()
    common.assert_no_model_imports()
    common.check_freeze()
    common.check_signoff()

    grid = json.loads((common.CONFIGS / "grid.json").read_text(encoding="utf-8"))["combos"]
    rows = grid
    if args.stage:
        rows = [r for r in rows if r["stage"] == args.stage]
    if args.only:
        want = {x.strip() for x in args.only.split(",")}
        rows = [r for r in rows if r["combo_id"] in want]
    if not rows:
        raise SystemExit("没有匹配的组合")

    ben, mal = data.load_benign(), data.load_malicious()
    cap_b, cap_m = gate.entity_capacity(ben.field_len), gate.entity_capacity(mal.field_len)
    cache = {}
    out = []
    for i, row in enumerate(rows, 1):
        out.append(run_row(row, ben, mal, cap_b, cap_m, cache))
        print(f"[{i}/{len(rows)}] {row['combo_id']} {row['label']} "
              f"误拦 {out[-1]['benign_denied']}/{out[-1]['benign_n']} "
              f"F1 {out[-1]['F1_rate']} F7 {out[-1]['F7_rate']}", flush=True)

    fields = list(out[0].keys())
    path = common.ROOT / args.out
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(f"落盘：{path}（{len(out)} 行）")
    if args.json_out:
        common.write_json(common.ROOT / args.json_out, {"rows": out, "n": len(out)})

    checks = {"rows": len(out), "guard": common.GUARD.report()}
    if len(out) == len(grid):
        checks["g_g_clone_rows"] = check_clone_rows(out)
        if checks["g_g_clone_rows"]["mismatch"]:
            raise common.SpikeStop(f"G-G 等价行不一致：{checks['g_g_clone_rows']['detail']}")
        by = {r["combo_id"]: r for r in out}
        checks["regression"] = {"C001": by["C001"]["benign_denied"],
                                "C006": by["C006"]["benign_denied"]}
        if by["C001"]["benign_denied"] != 38 or by["C006"]["benign_denied"] != 11:
            raise common.SpikeStop(f"回归破坏：C001={by['C001']['benign_denied']} "
                                   f"C006={by['C006']['benign_denied']}")
        common.write_json(common.ROOT / args.checks_out, checks)
    print(f"checks: {json.dumps({k: v for k, v in checks.items() if k != 'guard'}, ensure_ascii=False)[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
