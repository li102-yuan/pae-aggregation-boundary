# -*- coding: utf-8 -*-
"""data.py — 两侧数据重建（窗口 §5 步骤 1–2）。**只用既有确定性数据，不造字节。**

良性侧（68 个 holdout 可写任务）
    来源：`src/mcp/sanity/bench_full.py` 的同一条 builder 链
    （`source.load_tasks/load_db` → `carrier.build_task`），字段文本从
    `configs/sanity/data/retail_db.json` 逐字规范化得到，不做任何补写。
    自检：①每个 `(entity, field)` 的规范文本长度 == `store` 登记的 `field_len`；
         ②任务数 114 / 可写 104 / holdout 可写 68 与冻结件一致；
         ③逐调用 `(offset, len)` 与 `analysis/w101_coverage.csv` 的 ARM-KB 行一致。

恶意侧（`F1` 72 对、`F7` 22 对）
    来源：`src/attack/adaptive/families.py` 的生成器 + `state_store_v2.json` 的秘密值
    + `scenarios/s2b_adaptive/pairs/<pair>/manifest.json` 的 ctx。
    自检：逐片 `sha256(content) == calls.jsonl[*].fragments[*].content_sha256`，
    任一片对不上即 `DATA_RECONSTRUCTION_FAILED`（窗口 §11），不得用假内容凑。
"""
from __future__ import annotations

import csv
import dataclasses
import hashlib
import json

from src.spike.w11_matching import common
from src.spike.w11_matching.common import SpikeStop

# 只读复用（不修改原文件）
from src.attack.adaptive import families as FAM          # noqa: E402
from src.mcp.sanity import carrier as CAR                # noqa: E402
from src.mcp.sanity import source as SRC                 # noqa: E402


@dataclasses.dataclass(frozen=True)
class Frag:
    """一次调用里的一个片段。`true_*` 是**内容真实来源**（L2／M0 用），不是声明值。"""
    entity: str
    field: str
    offset: int
    length: int
    content: bytes
    encoding: str
    channel: str
    true_entity: str
    true_field: str
    true_offset: int
    secret_pos: int | None = None      # 恶意侧：该片在秘密里的起点；良性侧为 None

    def key(self):
        return (self.entity, self.field)


@dataclasses.dataclass
class Episode:
    episode_id: str
    task_id: str
    split: str
    calls: list[list[Frag]]
    truth_key: tuple[str, str]        # 秘密所在字段（良性＝被写字段；恶意＝目标字段）
    truth_len: int
    declared_channels: tuple = ()      # 任务声明的合法目的地（跑前可见）
    declared_cells: tuple = ()         # 任务声明的合法 cell（＝能力隔离的授权集）


@dataclasses.dataclass
class World:
    name: str
    episodes: list[Episode]
    field_len: dict[tuple[str, str], int]     # 分母来源（可信长度）
    field_text: dict[tuple[str, str], bytes]  # M1／M2 的索引源
    meta: dict


# ---------------------------------------------------------------- 良性
def _field_text_of(db, entity, field):
    for table in ("orders", "users"):
        record = db.get(table, {}).get(entity)
        if record is not None and field in record:
            text, _ = CAR.field_text(record[field])
            return text.encode("utf-8")
    raise SpikeStop(f"db 中找不到字段：{entity}.{field}")


def load_benign():
    carrier = common.load_json(common.INPUTS["carrier_v2"])
    tasks = SRC.load_tasks()
    db = SRC.load_db()
    split = common.load_json(common.INPUTS["split_w101"])

    built_all = []
    for task in tasks:
        built = CAR.build_task(task, db, carrier)
        for step in built["steps"]:
            step["channel"] = CAR.channel_string(step["channel_kind"], built["task_id"], carrier)
        built_all.append(built)

    if len(built_all) != 114:
        raise SpikeStop(f"良性重建：任务数 {len(built_all)} != 114")
    writable = [b for b in built_all if b["steps"]]
    if len(writable) != 104:
        raise SpikeStop(f"良性重建：可写任务 {len(writable)} != 104")

    field_len, field_text = {}, {}
    for built in built_all:
        for entry in built["store"]:
            key = (entry["entity"], entry["field"])
            text = _field_text_of(db, entry["entity"], entry["field"])
            if len(text) != entry["field_len"]:
                raise SpikeStop(
                    f"字段文本长度不符：{entry['entity']}.{entry['field']} "
                    f"重建 {len(text)} != 登记 {entry['field_len']}")
            if key in field_len and field_len[key] != entry["field_len"]:
                raise SpikeStop(f"字段总长冲突：{key}")
            field_len[key] = entry["field_len"]
            field_text[key] = text

    holdout = set(split["holdout_ids"])
    rows = []
    for built in writable:
        calls = [[Frag(entity=s["entity"], field=s["field"], offset=int(s["offset"]),
                       length=int(s["len"]), content=s["content"].encode("utf-8"),
                       encoding="none", channel=s["channel"],
                       true_entity=s["entity"], true_field=s["field"],
                       true_offset=int(s["offset"]))]
                 for s in built["steps"]]
        rows.append({"task_id": built["task_id"], "calls": calls,
                     "split": "holdout" if built["task_id"] in holdout else "dev"})
    episodes = [_episode_of(row, field_len,
                            {CAR.channel_string(kind, row["task_id"], carrier)
                             for kind in ("file", "http", "mail")})
                for row in rows]
    meta = {
        "tasks_total": len(built_all),
        "tasks_writable": len(writable),
        "holdout_writable": sum(1 for e in episodes if e.split == "holdout"),
        "dev_writable": sum(1 for e in episodes if e.split == "dev"),
        "fields_indexed": len(field_len),
        "bytes_indexed": sum(len(t) for t in field_text.values()),
        "min_fragment_len": min(len(f.content) for e in episodes for c in e.calls for f in c),
        "fragments": sum(len(c) for e in episodes for c in e.calls),
        "multi_field_tasks": sum(1 for e in episodes
                                 if len({f.key() for c in e.calls for f in c}) > 1),
    }
    return World(name="benign", episodes=episodes, field_len=field_len,
                 field_text=field_text, meta=meta)


def _episode_of(row, field_len, declared_channels):
    """truth_key：本次任务里被覆盖字节最多的字段（良性任务可有多个字段）。"""
    totals = {}
    for call in row["calls"]:
        for frag in call:
            totals[frag.key()] = totals.get(frag.key(), 0) + frag.length
    key = max(totals, key=lambda k: (totals[k], k))
    return Episode(episode_id=f"benign/{row['task_id']}", task_id=row["task_id"],
                   split=row["split"], calls=row["calls"], truth_key=key,
                   truth_len=field_len[key],
                   declared_channels=tuple(sorted(declared_channels)),
                   declared_cells=tuple(sorted(totals)))


# ---------------------------------------------------------------- 恶意
def _manifest(pair_id):
    path = common.ROOT / "scenarios" / "s2b_adaptive" / "pairs" / pair_id / "manifest.json"
    return common.load_json(path)


def load_malicious(families=("F1", "F7")):
    store = common.load_json(common.INPUTS["w102_state_store_v2"])["entities"]
    pairs_csv = list(csv.DictReader(common.INPUTS["w102_pairs"].open(encoding="utf-8")))
    fam_cfg = common.load_json(common.INPUTS["w102_families"])

    field_len, field_text = {}, {}
    for entity, fields in store.items():
        for field, spec in fields.items():
            key = (entity, field)
            value = spec["value"]
            if len(value.encode("utf-8")) != int(spec["field_len"]):
                raise SpikeStop(f"state_store_v2 长度不符：{key}")
            field_len[key] = int(spec["field_len"])
            field_text[key] = value.encode("utf-8")

    # 逐片 content_sha256（budget=8 那一档；两档结构相同，内容同）
    want = {}
    for line in common.INPUTS["w102_calls"].open(encoding="utf-8"):
        row = json.loads(line)
        if row["family"] not in families or int(row["budget"]) != 8:
            continue
        want.setdefault((row["family"], row["pair_id"], row["call_index"]), []).append(
            [f["content_sha256"] for f in row["fragments"]])

    pair_ids = sorted({(fam, pid) for (fam, pid, _idx) in want})
    episodes, checked, mismatched = [], 0, []
    for family, pair_id in pair_ids:
        man = _manifest(pair_id)
        ctx = dict(man)
        ctx.update({"family": family, "budget": 8, "variant": 0})
        gen = FAM.GENERATORS[family](ctx)
        calls, index = [], 1
        while True:
            try:
                yielded = gen.send({"ok": True}) if index > 1 else next(gen)
            except StopIteration:
                break
            out = []
            for frag in yielded:
                secret_pos = int(frag.spans[0][0]) if frag.spans else None
                out.append(Frag(
                    entity=frag.entity, field=frag.field, offset=int(frag.offset),
                    length=int(frag.length), content=frag.content.encode("utf-8"),
                    encoding=frag.encoding, channel=frag.channel,
                    true_entity=man["target"]["entity"], true_field=man["target"]["field"],
                    true_offset=(secret_pos if secret_pos is not None else int(frag.offset)),
                    secret_pos=secret_pos))
            calls.append(out)
            # 逐片对 content_sha256
            expect = want.get((family, pair_id, index))
            if expect is None:
                mismatched.append(f"{pair_id}#{index}: calls.jsonl 无此调用")
            else:
                got = [common.sha256_bytes(f.content) for f in out]
                if len(expect[0]) != len(got) or expect[0] != got:
                    mismatched.append(f"{pair_id}#{index}: 片段摘要不符")
                else:
                    checked += len(got)
            index += 1
            if index > 16:
                raise SpikeStop(f"{pair_id}：生成器未在 16 次调用内收敛")

        episodes.append(Episode(
            episode_id=f"{family}/{pair_id}", task_id=pair_id, split=man["side"],
            calls=calls, truth_key=(man["target"]["entity"], man["target"]["field"]),
            truth_len=int(man["target"]["field_len"]),
            declared_channels=tuple(sorted(set(man["alternates"]["channels"].values()))),
            declared_cells=((man["target"]["entity"], man["target"]["field"]),)))

    if mismatched:
        raise SpikeStop("DATA_RECONSTRUCTION_FAILED：" + "; ".join(mismatched[:5])
                        + f"（共 {len(mismatched)} 处）")

    meta = {
        "pairs": {fam: len({pid for (f, pid) in pair_ids if f == fam}) for fam in families},
        "fragments": sum(len(c) for e in episodes for c in e.calls),
        "content_sha256_checked": checked,
        "fields_indexed": len(field_len),
        "bytes_indexed": sum(len(t) for t in field_text.values()),
        "budgets": fam_cfg.get("budget", fam_cfg.get("budgets")),
    }
    return World(name="malicious", episodes=episodes, field_len=field_len,
                 field_text=field_text, meta=meta)


# ---------------------------------------------------------------- 交叉自检
def check_against_w101(world):
    """良性逐调用 `(offset, len, entity, field)` 必须与 ARM-KB 的覆盖行一致。

    注意 `analysis/w101_coverage.csv` 只登记**被拒调用**（120 行），故这里只做
    「被拒行能否在重建里找到同样的坐标」这一方向的核对；反向（重建里的每个调用
    是否都被登记）不成立也不应成立。真正的逐调用一致性由 baseline 重放负责。
    """
    rows = [r for r in csv.DictReader(common.INPUTS["w101_coverage"].open(encoding="utf-8"))
            if r["arm"] == "ARM-KB"]
    by_task = {}
    for episode in world.episodes:
        by_task[episode.task_id] = episode
    bad = []
    for row in rows:
        episode = by_task.get(row["task_id"])
        if episode is None:
            bad.append(f"{row['task_id']}: 重建里无此任务")
            continue
        idx = int(row["call_index"]) - 1
        if idx >= len(episode.calls):
            bad.append(f"{row['task_id']}#{row['call_index']}: 重建调用数不足")
            continue
        frag = episode.calls[idx][0]
        got = (frag.entity, frag.field, frag.offset, frag.length)
        exp = (row["entity"], row["field"], int(row["offset"]), int(row["len"]))
        if got != exp:
            bad.append(f"{row['task_id']}#{row['call_index']}: {got} != {exp}")
    if bad:
        raise SpikeStop("良性重建与 w101_coverage 不符：" + "; ".join(bad[:5]))
    return {"checked_rows": len(rows), "mismatch": 0}
