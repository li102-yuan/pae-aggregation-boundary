# -*- coding: utf-8 -*-
"""baseline.py — S-1 基线自检（窗口 §5 步骤 3）。

**不用自研实现**：良性侧直接调用 `src/gate/history.py::HistoryGate`（只读 import，
quota 全 null ⇒ K_B-only，与 `ARM-KB` 同构），逐调用与 `analysis/w101_coverage.csv`
的 120 条拒行比对：调用号、覆盖率、拒因必须逐项相同。

恶意侧：`L1/S1/D1/θ=0.55` 重放 F1／F7，必须复现 `analysis/w102_pairs.csv`
的 `r2=1`、`deny_at` 空、`F1 72/72`、`F7 20/20`。
"""
from __future__ import annotations

import csv

from src.gate.history import HistoryGate
from src.spike.w11_matching import common, data, gate
from src.spike.w11_matching.common import SpikeStop

THETA = 0.55
MAX_BENIGN = 0.416667       # 冻结件 theta.lower_bound，逐字取自 w32_freeze_v1.json


def _gate():
    if abs(common.load_json(common.POLICY)["theta"]["value"] - THETA) > 1e-12:
        raise SpikeStop("现行 θ 不是 0.55：不得继续（窗口 §2 第 4 条）")
    return HistoryGate(theta=THETA, quota_count=None, quota_bytes=None,
                       max_benign_coverage=MAX_BENIGN, config_hash="spike:baseline")


def replay_benign_history(world):
    """用现行 HistoryGate 逐调用重放；返回 {task_id: [(decision, reason, coverage, would_be)]}。"""
    gate_obj = _gate()
    for (entity, field), total in world.field_len.items():
        gate_obj.register_field(entity, field, total)
    out = {}
    for episode in world.episodes:
        gate_obj.reset(episode.episode_id)
        rows = []
        committed = {}
        for call in episode.calls:
            frags = [{"entity_id": f.entity, "field": f.field, "offset": f.offset,
                      "len": f.length, "encoding": f.encoding, "channel": f.channel,
                      "content": f.content.decode("utf-8")} for f in call]
            decision, reason, info = gate_obj.evaluate(frags, episode.episode_id)
            would = info.get("coverage")
            rows.append((decision, reason, info.get("coverage_committed"), would))
        out[episode.task_id] = rows
    return out


def check_benign(world):
    got = replay_benign_history(world)
    rows = [r for r in csv.DictReader(common.INPUTS["w101_coverage"].open(encoding="utf-8"))
            if r["arm"] == "ARM-KB"]

    expected_denies = {}
    for row in rows:
        expected_denies.setdefault(row["task_id"], {})[int(row["call_index"])] = row

    mismatch = []
    for task_id, per_call in got.items():
        expect = expected_denies.get(task_id, {})
        for index, (decision, reason, _committed, would) in enumerate(per_call, 1):
            want = expect.get(index)
            if want is None:
                if decision != "allow":
                    mismatch.append(f"{task_id}#{index}: 重建判 deny({reason})，w101 无此拒行")
                continue
            if decision != "deny":
                mismatch.append(f"{task_id}#{index}: 重建判 allow，w101 记 deny")
                continue
            if reason != want["deny_reason"]:
                mismatch.append(f"{task_id}#{index}: 拒因 {reason} != {want['deny_reason']}")
            if would is None or abs(would - float(want["cov_would_be"])) > 1e-6:
                mismatch.append(f"{task_id}#{index}: coverage {would} != {want['cov_would_be']}")

    holdout = [e for e in world.episodes if e.split == "holdout"]
    denied = [t for t in (e.task_id for e in holdout)
              if any(d == "deny" for d, _r, _c, _w in got[t])]
    return {
        "tasks": len(holdout), "denied": len(denied), "denied_ids": sorted(denied),
        "deny_rows_checked": len(rows), "mismatch": mismatch,
        "rate": len(denied) / len(holdout),
        "wilson": gate.wilson(len(denied), len(holdout)),
    }


def check_m0(world_benign, world_mal):
    """M0：用 `src/observe/ref.py` 独立复算离线 oracle 标签。

    ①良性：每一步 `status()["coverage"]` 必须与 `ref.coverage` 的最大比率逐点相等（1e-12）；
    ②恶意：F1／F7 的**全部**片段交付后 `ref.reconstructable` 仍为 False（R1=0/72、0/22），
      而内容级真值为 100%——这就是 R1／R2 分裂的 M0 侧复现。
    """
    from src.observe import ref as REF

    gate_obj = _gate()
    for (entity, field), total in world_benign.field_len.items():
        gate_obj.register_field(entity, field, total)
    diffs = []
    for episode in world_benign.episodes:
        gate_obj.reset(episode.episode_id)
        delivered = []
        for index, call in enumerate(episode.calls, 1):
            frags = [{"entity_id": f.entity, "field": f.field, "offset": f.offset,
                      "len": f.length, "encoding": f.encoding, "channel": f.channel,
                      "content": f.content.decode("utf-8")} for f in call]
            decision, _reason, _info = gate_obj.evaluate(frags, episode.episode_id)
            if decision == "allow":
                delivered.extend(frags)
            got = gate_obj.status(episode.episode_id)["coverage"]
            cov = REF.coverage(delivered, world_benign.field_len)
            want = max((item["ratio"] for item in cov.values()), default=0.0)
            if abs(got - want) > 1e-12:
                diffs.append(f"{episode.episode_id}#{index}: gate {got} != ref {want}")

    mal = {}
    for episode in world_mal.episodes:
        frags = [{"entity_id": f.entity, "field": f.field, "offset": f.offset,
                  "len": f.length, "encoding": f.encoding,
                  "content": f.content.decode("utf-8")}
                 for call in episode.calls for f in call]
        mal.setdefault(episode.episode_id.split("/")[0], []).append(
            REF.reconstructable(frags, world_mal.field_len))
    return {
        "benign_points": sum(len(e.calls) for e in world_benign.episodes),
        "benign_mismatch": diffs[:5], "benign_mismatch_n": len(diffs),
        "malicious_r1": {fam: {"n": len(v), "reconstructable": sum(1 for x in v if x)}
                         for fam, v in mal.items()},
    }


def check_malicious(world):
    """L1/S1/D1/θ=0.55：F1／F7 必须全 BYPASS（deny_any=0、内容 100% 交付）。"""
    cap = gate.entity_capacity(world.field_len)
    rule = gate.Rule(scope="S1", denom="D1", lineage="L1", theta=THETA, dest="off")
    by_family = {}
    for episode in world.episodes:
        result = gate.replay(episode, rule, None, world.field_len, cap)
        family = episode.episode_id.split("/")[0]
        by_family.setdefault(family, []).append((episode, result))
    out = {}
    for family, items in by_family.items():
        judged = [(e, r) for e, r in items if e.split == "test"] if family == "F7" else items
        bypass = sum(1 for _e, r in judged if not r.intercepted)
        out[family] = {
            "executed": len(items), "judged": len(judged),
            "bypass": bypass, "deny_any": sum(1 for _e, r in judged if r.deny_any),
            "complete_delivery": sum(1 for _e, r in judged
                                     if r.delivered_truth_bytes == r.truth_len),
            "ids": [e.episode_id for _e, r in judged if r.intercepted],
        }
    return out
