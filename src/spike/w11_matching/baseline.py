# -*- coding: utf-8 -*-
"""Reproduce the frozen baseline readings (68-task holdout, F1/F7 judgement sets)."""
from __future__ import annotations

import csv

from src.gate.history import HistoryGate
from src.spike.w11_matching import common, data, gate
from src.spike.w11_matching.common import SpikeStop

THETA = 0.55
MAX_BENIGN = 0.416667


def _gate():
    if abs(common.load_json(common.POLICY)["theta"]["value"] - THETA) > 1e-12:
        raise SpikeStop("现行 θ 不是 0.55：不得继续（窗口 §2 第 4 条）")
    return HistoryGate(theta=THETA, quota_count=None, quota_bytes=None,
                       max_benign_coverage=MAX_BENIGN, config_hash="spike:baseline")


def replay_benign_history(world):
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
