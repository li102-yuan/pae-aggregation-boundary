# -*- coding: utf-8 -*-
"""recut.py — 良性侧「写单元」重切（`W11.4` T2）。**只动良性侧。**

做一件事：把良性 episode 的每个写片段按冻结粒度切成**连续**小片，每片独立成一次调用
（"单次写单元"的字面含义：一次调用最多写这么多字节）。**总字节数不变、序不变、
内容逐字节取自原片段**（不造字节）。

粒度定义（`configs/w11geom/PREREG_GEOM.json` 冻结，本文件只是它的实现）：

| 档 | kind | 单次写单元 |
|---|---|---|
| `G1` | `identity` | 不切（回归锚点：必须逐字节等于 `W11.SPIKE` 的良性世界） |
| `G2` | `ratio` 1/2 | `max(1, ⌊field_len × 1/2⌋)` |
| `G3` | `ratio` 1/4 | `max(1, ⌊field_len × 1/4⌋)` |
| `G4` | `ratio` 1/8 | `max(1, ⌊field_len × 1/8⌋)` |
| `G5` | `cap` 3 | 绝对上限 **3 B**（低于 `M2` 的 `ℓ_min=8`，极端档） |

**为什么是 `field_len × 比例` 而不是 `片段长 × 比例`**：窗口 §T1 的字面定义是
「目标单次写单元 ＝ 字段长 × 比例」，含义是「一次调用最多写掉字段的这个比例」，
即对 per-call 覆盖率的**上限约束**；片段本身已小于该上限时不动（不制造无意义切分）。
两种读法在 `L1` 臂上给出**完全相同**的读数（见 `reports/spike/w11geom_report.md` §5
的不变性引理），差别只在细分档实际发生的切分次数，故此处从字面并在报告里逐档披露
`split_fragments / fragments`。

**单调性提示**：`G5` 是绝对下限、`G4` 是相对比例，故 `field_len < 24` 的字段上
`G4` 的单位（`field_len/8`）**小于** `G5` 的 3 B——`G4` 比 `G5` 更碎。报告须披露，
不得把 `G5` 当成"最碎的一档"。
"""
from __future__ import annotations

import dataclasses
import statistics

from src.gate.history import _covered_bytes, _merge
from src.spike.w11_matching import data
from src.spike.w11_matching.common import SpikeStop

GEOM_ORDER = ("G1", "G2", "G3", "G4", "G5")

# 与 `PREREG_GEOM.json` 的 `geometries` 逐字对应；`run_geom` 会先断言两者一致。
GEOM = {
    "G1": {"kind": "identity", "ratio": None, "unit": None},
    "G2": {"kind": "ratio", "ratio": [1, 2], "unit": None},
    "G3": {"kind": "ratio", "ratio": [1, 4], "unit": None},
    "G4": {"kind": "ratio", "ratio": [1, 8], "unit": None},
    "G5": {"kind": "cap", "ratio": None, "unit": 3},
}


def unit_for(spec, field_len):
    """该字段在本档下的单次写单元（字节）。`None` ＝ 不切。"""
    kind = spec["kind"]
    if kind == "identity":
        return None
    if kind == "cap":
        return int(spec["unit"])
    if kind != "ratio":
        raise SpikeStop(f"未知粒度 kind：{kind}")
    num, den = spec["ratio"]
    return max(1, int(field_len) * int(num) // int(den))


def split_fragment(frag, unit):
    """→ [Frag]；连续切、偏移同步平移、内容取自原片段切片。`unit=None` 或片已够小则原样。"""
    if unit is None or frag.length <= unit:
        return [frag]
    pieces, start = [], 0
    while start < frag.length:
        take = min(unit, frag.length - start)
        pieces.append(dataclasses.replace(
            frag,
            offset=frag.offset + start,
            length=take,
            content=frag.content[start:start + take],
            true_offset=frag.true_offset + start,
        ))
        start += take
    if b"".join(p.content for p in pieces) != frag.content:
        raise SpikeStop(f"切片内容不等于原片段：{frag.key()} off={frag.offset}")
    if sum(p.length for p in pieces) != frag.length:
        raise SpikeStop(f"切片长度不守恒：{frag.key()} off={frag.offset}")
    return pieces


def recut_episode(episode, spec, field_len):
    """一 episode → 重切后的 episode；一片一次调用（序 = 原序）。"""
    calls = []
    for call in episode.calls:
        for frag in call:
            unit = unit_for(spec, field_len[frag.key()])
            for piece in split_fragment(frag, unit):
                calls.append([piece])
    return dataclasses.replace(episode, calls=calls)


def _spans_by_key(episode):
    out = {}
    for call in episode.calls:
        for frag in call:
            out.setdefault(frag.key(), []).append((frag.offset, frag.offset + frag.length))
    return {k: _merge(v) for k, v in out.items()}


def check_conservation(old, new, field_text):
    """逐 episode 断言：①字节流逐字相等 ②逐字段区间并集相等 ③覆盖相等 ④内容取自字段。"""
    if len(old.episodes) != len(new.episodes):
        raise SpikeStop("重切后 episode 数变了")
    checked = {"episodes": 0, "fragments": 0, "bytes": 0, "keys": 0}
    for a, b in zip(old.episodes, new.episodes):
        if a.episode_id != b.episode_id:
            raise SpikeStop(f"episode 序错位：{a.episode_id} != {b.episode_id}")
        if a.truth_key != b.truth_key or a.truth_len != b.truth_len:
            raise SpikeStop(f"truth 变了：{a.episode_id}")
        if a.split != b.split or a.declared_cells != b.declared_cells:
            raise SpikeStop(f"declared/split 变了：{a.episode_id}")
        old_stream = b"".join(f.content for c in a.calls for f in c)
        new_stream = b"".join(f.content for c in b.calls for f in c)
        if old_stream != new_stream:
            raise SpikeStop(f"字节流不等：{a.episode_id}")
        sa, sb = _spans_by_key(a), _spans_by_key(b)
        if set(sa) != set(sb):
            raise SpikeStop(f"触及字段集变了：{a.episode_id}")
        for key in sa:
            if sa[key] != sb[key]:
                raise SpikeStop(f"区间并集变了：{a.episode_id} {key}")
            cov_a = _covered_bytes(sa[key], old.field_len[key])
            cov_b = _covered_bytes(sb[key], old.field_len[key])
            if cov_a != cov_b:
                raise SpikeStop(f"覆盖变了：{a.episode_id} {key}")
        for call in b.calls:
            for frag in call:
                hay = field_text[frag.key()]
                if hay[frag.offset:frag.offset + frag.length] != frag.content:
                    raise SpikeStop(f"内容不是字段切片：{a.episode_id} {frag.key()}")
        checked["episodes"] += 1
        checked["fragments"] += sum(len(c) for c in b.calls)
        checked["bytes"] += len(new_stream)
        checked["keys"] += len(sa)
    return checked


def _stats(geometry, old, new, spec=None):
    lens = [f.length for e in new.episodes for c in e.calls for f in c]
    frags = sum(len(c) for e in old.episodes for c in e.calls for f in c)
    pieces = len(lens)
    split = 0
    if spec is not None:
        for ep in old.episodes:
            for call in ep.calls:
                for frag in call:
                    unit = unit_for(spec, old.field_len[frag.key()])
                    if unit is not None and frag.length > unit:
                        split += 1
    return {
        "geometry": geometry,
        "episodes": len(new.episodes),
        "fragments_in": frags,
        "pieces_out": pieces,
        "split_fragments": split,
        "calls_in": sum(len(e.calls) for e in old.episodes),
        "calls_out": sum(len(e.calls) for e in new.episodes),
        "bytes_total": sum(lens),
        "min_piece": min(lens) if lens else None,
        "median_piece": statistics.median(lens) if lens else None,
        "max_piece": max(lens) if lens else None,
        "pieces_lt8": sum(1 for n in lens if n < 8),
        "pieces_lt4": sum(1 for n in lens if n < 4),
    }


def recut_world(world, geometry):
    """→ (新 World, 统计)。`field_len` / `field_text` 原样带给匹配器（索引建在字段上，不建在片段上）。"""
    spec = GEOM[geometry]
    episodes = [recut_episode(ep, spec, world.field_len) for ep in world.episodes]
    new = data.World(name=f"{world.name}/{geometry}", episodes=episodes,
                     field_len=world.field_len, field_text=world.field_text,
                     meta=dict(world.meta))
    checked = check_conservation(world, new, world.field_text)
    stats = _stats(geometry, world, new, spec)
    stats["conservation"] = checked
    new.meta["recut"] = stats
    return new, stats


def selftest():
    """冻结前自检：只做重切层的守恒断言，**不跑任何判定**（不产生候选读数）。"""
    world = data.load_benign()
    report = []
    base = None
    for geometry in GEOM_ORDER:
        new, stats = recut_world(world, geometry)
        if geometry == "G1":
            base = [(f.entity, f.field, f.offset, f.length, f.content)
                    for e in new.episodes for c in e.calls for f in c]
            orig = [(f.entity, f.field, f.offset, f.length, f.content)
                    for e in world.episodes for c in e.calls for f in c]
            if base != orig:
                raise SpikeStop("G1 不是恒等重切")
            if stats["pieces_out"] != stats["fragments_in"]:
                raise SpikeStop("G1 片段数变了")
        if stats["bytes_total"] != sum(
                f.length for e in world.episodes for c in e.calls for f in c):
            raise SpikeStop(f"{geometry} 总字节不守恒")
        report.append(stats)
    return report


def main():
    rows = selftest()
    for r in rows:
        print(f"{r['geometry']}: 片段 {r['fragments_in']} → 片 {r['pieces_out']} "
              f"（{r['split_fragments']} 个片段被切）调用 {r['calls_in']} → {r['calls_out']} "
              f"字节 {r['bytes_total']} | 片长 {r['min_piece']}–{r['max_piece']} "
              f"中位 {r['median_piece']} | <8B {r['pieces_lt8']} <4B {r['pieces_lt4']}")
    print("SELFTEST=PASS（五档全部逐任务守恒；G1 恒等）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
