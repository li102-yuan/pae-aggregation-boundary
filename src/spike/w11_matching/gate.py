# -*- coding: utf-8 -*-
"""gate.py — 参数化重放引擎（候选规则的唯一实现）。

与 `src/gate/history.py` 的关系：**只读复用**其区间并集（`_merge` / `_covered_bytes`），
判据语义按窗口 §4 的三个新增维度重写；原文件一字未改。

一条规则 = `Rule(scope, denom, lineage, theta, matcher, norm, unmatched, dest)`：

| 维度 | 取值 | 含义 |
|---|---|---|
| `scope` | S1/S2/S3 | 单字段／同实体跨字段／全局会话 |
| `denom` | D1/D2 | 范围内字段总容量（朴素）／oracle 目标长度 |
| `lineage` | L1/L2/L3/L3c | 无归属／oracle 归属／M2 内容推断归属／L3+声明一致优先 |
| `theta` | 0.55…1.0 | 判定阈值（**不改**冻结件的 θ，只作候选网格参数） |
| `matcher` | none/M1/M2/M2-null/M2-short | 归属来源（L1/L2 不用） |
| `norm` | declared/all4 | 匹配前的归一化范围 |
| `unmatched` | allow/deny | 内容匹配不到时的处置（回落声明坐标／直接拒） |
| `dest` | off/chan/cell | 目的地授权粒度（cell＝能力隔离，单列） |
"""
from __future__ import annotations

import dataclasses

from src.gate.history import _covered_bytes, _merge
from src.spike.w11_matching.common import SpikeStop


@dataclasses.dataclass(frozen=True)
class Rule:
    scope: str = "S1"
    denom: str = "D1"
    lineage: str = "L1"
    theta: float = 0.55
    matcher: str = "none"
    norm: str = "all4"
    unmatched: str = "allow"
    dest: str = "off"

    def label(self):
        parts = [self.scope, self.denom, self.lineage, f"th={self.theta:g}"]
        if self.matcher != "none":
            parts.append(self.matcher)
            parts.append(f"norm={self.norm}")
            if self.lineage.startswith("L3"):
                parts.append(f"unm={self.unmatched}")
        if self.dest != "off":
            parts.append(f"dest={self.dest}")
        return "|".join(parts)

    def is_oracle(self):
        return self.lineage == "L2" or self.denom == "D2"


@dataclasses.dataclass
class CallResult:
    call_index: int
    decision: str
    reason: str
    coverage: float
    coverage_by_key: dict
    matched: int
    fragments: int
    ambiguous: int
    dest_violations: int


@dataclasses.dataclass
class EpisodeResult:
    episode_id: str
    rule: str
    calls: list
    deny_any: bool
    deny_at: int | None
    deny_reasons: list
    delivered_truth_bytes: int
    truth_len: int
    intercepted: bool
    matched_fragments: int
    total_fragments: int
    ambiguous_fragments: int
    max_coverage: float


def _ratio_key(k):
    """`_ratios` 的键：S1/S2 是 (entity, field) 或 entity 字符串；S3 是 `"*"`（W0.3 探针发现）。"""
    return f"{k[0]}::{k[1]}" if isinstance(k, tuple) else f"*::{k}"


def _covered(posted, key, field_len):
    total = field_len.get(key)
    if not total:
        return 0
    return _covered_bytes(posted[key], total)


def attribution(frag, rule, matcher):
    """→ ([(key, off, len)], status)；status ∈ {struct, oracle, matched, unmatched, fallback}。"""
    declared = (frag.key(), frag.offset, frag.length)
    if rule.lineage == "L1":
        return [declared], "struct"
    if rule.lineage == "L2":
        return [((frag.true_entity, frag.true_field), frag.true_offset, frag.length)], "oracle"
    if matcher is None:
        raise SpikeStop("L3 需要匹配器")
    hits = matcher.locate(frag.content, frag.encoding)
    if not hits:
        if rule.unmatched == "deny":
            return [], "unmatched"
        return [declared], "fallback"
    if rule.lineage == "L3c":
        own = [h for h in hits if h[0] == frag.key()]
        if own:
            return own, "matched"
    return hits, "matched"


def _ratios(posted, rule, field_len, entity_capacity, truth_len):
    cells = [k for k in posted if k in field_len]
    if rule.scope == "S1":
        return {k: _covered(posted, k, field_len) / field_len[k] for k in cells}
    if rule.scope == "S2":
        out = {}
        for key in cells:
            entity = key[0]
            cap = entity_capacity.get(entity) or 0
            if not cap:
                continue
            if rule.denom == "D1":
                out[entity] = out.get(entity, 0.0) + _covered(posted, key, field_len) / cap
            else:
                out[entity] = out.get(entity, 0.0) + _covered(posted, key, field_len) / truth_len
        return out
    entities = {k[0] for k in cells}
    if rule.denom == "D1":
        cap = sum(entity_capacity.get(e, 0) for e in entities) or 1
        return {"*": sum(_covered(posted, k, field_len) for k in cells) / cap}
    return {"*": sum(_covered(posted, k, field_len) for k in cells) / truth_len}


def replay(episode, rule, matcher, field_len, entity_capacity):
    committed = {}
    delivered = []
    calls = []
    allowed_channels = set(episode.declared_channels)

    for index, call in enumerate(episode.calls, 1):
        posted = {key: list(iv) for key, iv in committed.items()}
        statuses, ambiguous, dest_hits = [], 0, 0
        for frag in call:
            hits, status = attribution(frag, rule, matcher)
            statuses.append(status)
            if len(hits) > 1:
                ambiguous += 1
            if rule.dest == "cell" and frag.key() not in episode.declared_cells:
                dest_hits += 1
            if rule.dest == "chan" and frag.channel not in allowed_channels:
                dest_hits += 1
            for (key, off, length) in hits:
                posted.setdefault(key, []).append((off, off + length))

        ratios = _ratios(posted, rule, field_len, entity_capacity, episode.truth_len)
        coverage = max(ratios.values()) if ratios else 0.0

        if any(s == "unmatched" for s in statuses):
            decision, reason = "deny", "unmatched_content"
        elif dest_hits:
            decision, reason = "deny", "dest_violation"
        elif coverage >= rule.theta - 1e-12:
            decision, reason = "deny", "coverage_threshold"
        else:
            decision, reason = "allow", ""

        calls.append(CallResult(
            call_index=index, decision=decision, reason=reason, coverage=coverage,
            coverage_by_key={_ratio_key(k): round(v, 6) for k, v in ratios.items()},
            matched=sum(1 for s in statuses if s == "matched"),
            fragments=len(call), ambiguous=ambiguous, dest_violations=dest_hits))
        if decision == "allow":
            committed = {key: _merge(iv) for key, iv in posted.items()}
            delivered.extend(call)

    spans = [(f.true_offset, f.true_offset + f.length) for f in delivered
             if (f.true_entity, f.true_field) == episode.truth_key]
    got = _covered_bytes(spans, episode.truth_len)
    return EpisodeResult(
        episode_id=episode.episode_id, rule=rule.label(), calls=calls,
        deny_any=any(c.decision == "deny" for c in calls),
        deny_at=next((c.call_index for c in calls if c.decision == "deny"), None),
        deny_reasons=[c.reason for c in calls if c.decision == "deny"],
        delivered_truth_bytes=got, truth_len=episode.truth_len,
        intercepted=got < episode.truth_len,
        matched_fragments=sum(c.matched for c in calls),
        total_fragments=sum(c.fragments for c in calls),
        ambiguous_fragments=sum(c.ambiguous for c in calls),
        max_coverage=max((c.coverage for c in calls), default=0.0))


def entity_capacity(field_len):
    """每个实体的**全部已登记字段**容量（S2 的朴素分母；不由攻击者选哪些字段而变）。"""
    out = {}
    for (entity, _field), total in field_len.items():
        out[entity] = out.get(entity, 0) + total
    return out


# ---------------------------------------------------------------- 汇总与区间
def wilson(k, n, z=1.959963984540054):
    """Wilson 95% 双侧区间（任务级 cluster，不把调用当独立样本）。"""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def summarize(results, key="deny_any"):
    n = len(results)
    k = sum(1 for r in results if getattr(r, key))
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n) if n else None,
            "wilson_lo": lo, "wilson_hi": hi}
