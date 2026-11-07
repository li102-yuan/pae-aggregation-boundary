# -*- coding: utf-8 -*-
"""Write the frozen configuration files and bootstrap artefacts."""
from __future__ import annotations

import datetime
import hashlib
import itertools
import json
import platform
import sys

from src.spike.w11_matching import baseline, common, data, gate, matching
from src.spike.w11_matching.common import SpikeStop

THETAS = (0.55, 0.7, 0.8, 0.9, 0.95, 1.0)
SCOPES = (("S1", "D1"), ("S2", "D1"), ("S2", "D2"), ("S3", "D1"), ("S3", "D2"))

EXPECT = {"grid": 234, "adversary": 110, "go_eligible": 102}

ROLES = {
    "w101_coverage": "良性侧逐调用覆盖（ARM-KB 拒行，120 条）：S-1 逐调用比对的唯一外部锚点",
    "carrier_v2": "任务动作 → 字段/通道映射；良性目的地授权集来源",
    "retail_db": "良性字段真实文本（M1 明文/M2 指纹的索引源）",
    "bench_full": "只读复用其 builder 链（source→carrier.build_task），重建 built['steps'] 与 content",
    "carrier_py": "字段规范化与组件字节区间（build_task 的实现）",
    "source_py": "vendored 三件套装载与 sha256 校验",
    "split_w101": "holdout/dev 划分与可写分母 68",
    "w101_summary": "W10.1 五臂读数（38/68 的出处）",
    "w102_families": "族定义、pair_set、臂",
    "w102_state_store_v2": "合成秘密值（M1 明文对照、M2 指纹源）",
    "w102_pairs": "逐对 R1/R2/deny_at（S-1 恶意侧锚点）",
    "w102_summary": "族级基线读数",
    "w102_calls": "逐调用 fragments + content_sha256（重建校验）",
    "families_py": "F1/F7 生成器（只读复用，重建片段）",
    "construct_py": "pair manifest 构造规则（只读）",
    "construct_manifest": "构造清单（pair→manifest 映射与 sha256）",
    "ref_py": "M0 离线 oracle：解码、归一、区间并集、reconstructable",
    "history_py": "现行 K_B 语义与区间并集（只读 import）",
    "canonicalizer_py": "归一化（只读）",
    "policy": "现行 θ=0.55 的唯一来源",
}

PRIORS = [
    "P1 只加 scope／denominator 不会把误拦从 55.9% 降到 30% 以下——52.3% 的写动作自己就越 θ，"
    "换聚合键不改变这一点（W11.1 的 A1/A2/A6 稀释论证）。",
    "P2 M2 的内容匹配能补跨 cell 归属（L3），但不自动降低良性整字段写的误拦。",
    "P3 误拦要降，必须引入 DEST（或良性写豁免）；良性写豁免会被 C-B 打。",
    "P4 DEST-structural 是最 plausible 的 escape。",
    "P5 C-C unseen 一定不会 <10%；只能写成 claim 边界。",
]


def _combo(stage, scope, denom, lineage, theta, matcher="none", norm="all4",
           unmatched="allow", dest="off"):
    rule = gate.Rule(scope=scope, denom=denom, lineage=lineage, theta=theta,
                     matcher=matcher, norm=norm, unmatched=unmatched, dest=dest)
    return {
        "combo_id": None, "stage": stage,
        "scope": scope, "denom": denom, "lineage": lineage, "theta": theta,
        "matcher": matcher, "norm": norm, "unmatched": unmatched, "dest": dest,
        "label": rule.label(), "oracle": rule.is_oracle(),
        "deployable": (matcher in ("M2", "M2-short") and lineage in ("L3", "L3c")
                       and dest != "cell"),
        "go_eligible": (matcher in ("M2", "M2-short") and lineage in ("L3", "L3c")
                        and dest != "cell" and denom != "D2"),
    }


def build_grid():
    rows = []
    for (scope, denom) in SCOPES:
        for theta in THETAS:
            rows.append(_combo("G-A", scope, denom, "L1", theta))
    for matcher in ("M1", "M2"):
        for (scope, denom) in SCOPES:
            for theta in THETAS:
                rows.append(_combo("G-B", scope, denom, "L3", theta, matcher=matcher))
    for matcher in ("M1", "M2"):
        for (scope, denom) in SCOPES:
            for theta in THETAS:
                rows.append(_combo("G-C", scope, denom, "L3c", theta, matcher=matcher))
    for (scope, denom) in SCOPES:
        for theta in THETAS:
            rows.append(_combo("G-D", scope, denom, "L3", theta, matcher="M2",
                               unmatched="deny"))
    for theta in THETAS:
        rows.append(_combo("G-E", "S1", "D1", "L3", theta, matcher="M2", norm="declared"))
    for dest in ("chan", "cell"):
        for theta in THETAS:
            rows.append(_combo("G-F", "S1", "D1", "L3", theta, matcher="M2", dest=dest))
    for unmatched in ("allow", "deny"):
        for (scope, denom) in (("S1", "D1"), ("S2", "D1"), ("S3", "D1")):
            for theta in THETAS:
                rows.append(_combo("G-G", scope, denom, "L3", theta,
                                   matcher="M2-short", unmatched=unmatched))
    for index, row in enumerate(rows, 1):
        row["combo_id"] = f"C{index:03d}"
    return rows


def adversary_set(rows):
    out = []
    for row in rows:
        if row["stage"] in ("G-B", "G-C") and (row["scope"], row["denom"]) in (
                ("S1", "D1"), ("S2", "D1"), ("S3", "D1")):
            out.append(row["combo_id"])
        if row["stage"] == "G-F" and row["dest"] == "cell" and row["theta"] in (0.55, 1.0):
            out.append(row["combo_id"])
        if row["stage"] == "G-G":
            out.append(row["combo_id"])
    return out


# ---------------------------------------------------------------- FIX-3：S-4
def _spans(hits):
    return sorted((key[0], key[1], off, length) for (key, off, length) in hits)


def s4_agreement(world_benign, world_mal):
    out = {}
    for name, world in (("benign", world_benign), ("malicious", world_mal)):
        m1 = matching.build("M1", world.field_text)
        m2 = matching.build("M2", world.field_text)
        items = [(episode.episode_id, index, frag)
                 for episode in world.episodes
                 for index, call in enumerate(episode.calls, 1) for frag in call]
        same = matchable = unmatch = 0
        short_lens, short_ids, all_short_ids = [], [], []
        for position, (episode_id, call_index, frag) in enumerate(items):
            h1 = m1.locate(frag.content, frag.encoding)
            h2 = m2.locate(frag.content, frag.encoding)
            if len(frag.content) < min(matching.ELLS):
                all_short_ids.append(position)
                unmatch += 1
                if not h2:
                    short_lens.append(len(frag.content))
                    short_ids.append(position)
                continue
            matchable += 1
            same += int(_spans(h1) == _spans(h2))
        out[name] = {
            "fragments": len(items), "matchable": matchable, "byte_identical": same,
            "rate_matchable": (same / matchable) if matchable else None,
            "structurally_unmatchable": unmatch,
            "unmatchable_lens": sorted(set(short_lens)),
            "rate_all": (same / len(items)) if items else None,
            "unmatchable_set_equals_short_set": sorted(short_ids) == sorted(all_short_ids),
            "unmatchable_ids": [f"{items[i][0]}#{items[i][1]}" for i in short_ids],
            "unmatchable_episodes": sorted({items[i][0] for i in short_ids}),
        }
        if out[name]["rate_matchable"] is None or out[name]["rate_matchable"] < 0.99:
            raise SpikeStop(f"S-4 FAIL（{name}）：rate_matchable="
                            f"{out[name]['rate_matchable']} < 0.99")
        if any(length >= min(matching.ELLS) for length in out[name]["unmatchable_lens"]):
            raise SpikeStop(f"S-4 FAIL（{name}）：unmatchable_lens 出现 ≥8 ⇒ 真实现错")
        if not out[name]["unmatchable_set_equals_short_set"]:
            raise SpikeStop(f"S-4 FAIL（{name}）：不可匹配集合 ≠ 全部 len<8 片段集合")
    out["denominator"] = "matchable = len(content) >= min(ELLS)=8；rate_all 只披露，不作门禁"
    out["gate"] = "rate_matchable >= 0.99 且 unmatchable_lens 全部 < 8"
    return out


def main():
    common.GUARD.install()
    common.assert_no_model_imports()

    policy = common.load_json(common.POLICY)
    theta = policy["theta"]["value"]
    if abs(theta - common.THETA_EXPECTED) > 1e-12:
        raise SpikeStop(f"现行 θ={theta} != 0.55：窗口 §2 第 4 条禁止继续")
    if policy.get("status") != "frozen":
        raise SpikeStop("w32_freeze_v1.json 不是 frozen")

    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    print(f"[W11.SPIKE] bootstrap @ {stamp}", flush=True)

    benign = data.load_benign()
    print(f"[W11.SPIKE] 良性重建 OK：{benign.meta}", flush=True)
    w101 = data.check_against_w101(benign)
    print(f"[W11.SPIKE] 与 w101_coverage 交叉核对：{w101}", flush=True)

    mal = data.load_malicious()
    print(f"[W11.SPIKE] 恶意重建 OK：{mal.meta}", flush=True)

    s1 = baseline.check_benign(benign)
    print(f"[W11.SPIKE] S-1 良性：{s1['denied']}/{s1['tasks']} "
          f"mismatch={len(s1['mismatch'])}", flush=True)
    if s1["mismatch"]:
        raise SpikeStop("BASELINE_MISMATCH（良性）：" + "; ".join(s1["mismatch"][:5]))
    s1m = baseline.check_malicious(mal)
    print(f"[W11.SPIKE] S-1 恶意：{json.dumps(s1m, ensure_ascii=False)}", flush=True)
    m0 = baseline.check_m0(benign, mal)
    if m0["benign_mismatch_n"]:
        raise SpikeStop("BASELINE_MISMATCH（M0 良性）：" + "; ".join(m0["benign_mismatch"]))

    s4 = s4_agreement(benign, mal)
    print(f"[W11.SPIKE] S-4：benign {s4['benign']['byte_identical']}/"
          f"{s4['benign']['matchable']}、malicious {s4['malicious']['byte_identical']}/"
          f"{s4['malicious']['matchable']}、structurally_unmatchable="
          f"{s4['malicious']['structurally_unmatchable']} "
          f"lens={s4['malicious']['unmatchable_lens']}", flush=True)

    match_smoke = {}
    for name in ("M1", "M2", "M2-null"):
        matcher = matching.build(name, benign.field_text)
        frags = [f for e in benign.episodes for c in e.calls for f in c]
        hits = [matcher.locate(f.content, f.encoding) for f in frags]
        match_smoke[name] = {
            "fragments": len(frags),
            "matched": sum(1 for h in hits if h),
            "ambiguous": sum(1 for h in hits if len(h) > 1),
            "truth_contained": sum(
                1 for f, h in zip(frags, hits)
                if (f.key(), f.offset) in {(k, o) for k, o, _n in h}),
            "index_entries": getattr(matcher, "index_entries", 0),
            "hmac_calls": getattr(matcher, "hmac_calls", 0),
            "key_sha256": getattr(matcher, "key_sha256", None),
        }
    print(f"[W11.SPIKE] 匹配臂结构自检：{json.dumps(match_smoke, ensure_ascii=False)}",
          flush=True)

    grid = build_grid()
    adv = adversary_set(grid)
    go_eligible = [row for row in grid if row["go_eligible"]]
    assert len(grid) == EXPECT["grid"], f"grid {len(grid)} != {EXPECT['grid']}"
    assert len(adv) == EXPECT["adversary"], f"adversary {len(adv)} != {EXPECT['adversary']}"
    assert len(go_eligible) == EXPECT["go_eligible"], (
        f"go_eligible {len(go_eligible)} != {EXPECT['go_eligible']}")
    assert len(adv) == len(set(adv)), "adversary_combos 有重复"
    print(f"[W11.SPIKE] 网格计数：grid={len(grid)} adversary={len(adv)} "
          f"go_eligible={len(go_eligible)}（EXPECT 全过）", flush=True)
    sample = go_eligible[::max(1, len(go_eligible) // 10)][:10]
    print("[W11.SPIKE] go_eligible 抽样（G-FIX2）：" + "; ".join(
        f"{r['combo_id']} {r['matcher']}/{r['lineage']}/dest={r['dest']}/"
        f"{r['denom']}/oracle={r['oracle']}" for r in sample), flush=True)
    inputs = {
        "schema": "w11spike.inputs/v1",
        "window": "W11.SPIKE",
        "created_at": stamp,
        "note": "路径与 sha256 逐条登记；本 spike 只读这些文件，未写 runs/ 或 analysis/ 既有文件",
        "files": {},
    }
    for name, path in common.INPUTS.items():
        inputs["files"][name] = {
            "path": str(path.relative_to(common.ROOT)).replace("\\", "/"),
            "sha256": common.sha256_file(path),
            "bytes": path.stat().st_size,
            "role": ROLES[name],
        }

    prereg = {
        "schema": "w11spike.prereg/v1",
        "window": "W11.SPIKE",
        "created_at": stamp,
        "status": "PRE_SIGNOFF（SP1–SP5 未签；本文件之后不得回改，改动须记 DEVIATION_LEDGER）",
        "theta_policy": {
            "source": "configs/policy/w32_freeze_v1.json",
            "value": theta,
            "assert": "== 0.55，且 status=frozen",
            "explicitly_not_used": "configs/gate/history_v1.json（theta=1.0 是 provisional 暂定值）",
            "grid_theta_prime_is": "候选网格参数 θ′，不是部署 θ；不回头改冻结件",
        },
        "dimensions": {
            "scope": {"S1": "单字段（现状基线）", "S2": "同实体跨字段", "S3": "全局会话"},
            "denom": {"D1": "范围内字段总容量（朴素；S2＝该实体全部已登记字段，S3＝会话涉及实体的全部已登记字段）",
                    "D2": "oracle 目标长度（＝episode.truth_len）"},
            "lineage": {"L1": "无（纯结构）", "L2": "oracle 归属", "L3": "M2 内容推断归属（严格）",
                        "L3c": "L3 + 声明一致优先（声明 cell 命中时只记声明 cell）"},
            "matcher": {"M1": "明文模板匹配（正控制，不可上线）",
                        "M2": "HMAC-SHA256 盲索引，ℓ∈{8,16,32}，stride=1，key 每 run 随机、只存 sha256",
                        "M2-null": "同 M2 但 key 随机且不建索引（负控制）",
                        "M2-short": "ℓ∈{4,6,8,16,32}（敏感性，窗口规定的 ℓ 集之外）"},
            "norm": {"declared": "只按片段自报 encoding 解码", "all4": "依次尝试 none/base64/hex/homoglyph"},
            "unmatched": {"allow": "匹配不到时回落声明坐标（默认）", "deny": "匹配不到即拒（闭合世界白名单）"},
            "dest": {"off": "不判目的地", "chan": "通道级目的地授权（任务声明集）",
                     "cell": "cell 级写授权＝能力隔离（单列，不进 go 判定）"},
        },
        "definitions": {
            "误拦": "holdout 68 个可写任务中，episode 内至少一次 deny 的任务数／68（任务级 cluster）",
            "误拦_可匹配子集": "全部片段都能被当前匹配臂定位到的 holdout 任务；被排除的任务 id 必须逐条列出",
            "F1_拦截": "72 对中，内容级真值（秘密字节并集）在 episode 结束时 < truth_len 的对数／72",
            "F7_拦截": "执行 22 对；判定分母 20（side=test），dev 2 对单列不进判定",
            "漏匹配率": "未匹配片段数／片段总数（按匹配臂与 norm 统计）",
            "误匹配率": "匹配结果不含真实 (cell, offset) 的片段数／片段总数",
            "C-A": "把秘密等分成 n∈{2..6} 片，交替落 A.f／B.f 两个 cell；记拦截率",
            "C-B": "C-A(n=6) 之后把最后一片再切成 1 字节小片续写；记能否补齐最后字节",
            "C-C": "两片分别施加变换后提交；covered=四种已覆盖编码，heldout=base32/base64url/大写 hex，"
                   "unseen=zlib+base64/XOR/ROT13，noise=插入分隔符；漏匹配率按类分别报",
            "内容级真值": "只统计实际交付（allow）的片段，按其内容真实来源的字节区间求并集",
        },
        "grid": {
            "theta_prime": list(THETAS),
            "scope_denom": [list(x) for x in SCOPES],
            "combos": len(grid),
            "stages": {stage: sum(1 for r in grid if r["stage"] == stage)
                       for stage in ("G-A", "G-B", "G-C", "G-D", "G-E", "G-F", "G-G")},
            "adversary_combos": adv,
            "adversary_scope": "dest=cell 只取 θ′∈{0.55,1.0} 两端点；θ′=0.7/0.8/0.9/0.95 四档不单列"
                               "（dest=cell 的判定在 θ′ 上单调，端点包住区间）",
            "count_check": {"grid_combos": EXPECT["grid"], "adversary_combos": EXPECT["adversary"],
                            "go_eligible": EXPECT["go_eligible"]},
            "completeness": "缺一行即 S-5／G3 不过；每行必须带分母口径与 Wilson 区间",
            "G-D": "闭世界出口（unmatched=deny）；语义**不是**结构覆盖的自然延伸，"
                   "与 K_B 的 coverage 闭包不是同一回事，报告须单列",
        },
        "arithmetic_ceiling": {
            "cause": "M2 的 ℓ_min=8；F1 9 对、F7 4 对（judged）两片均 6 B（truth_len=12）"
                     "⇒ 任何 ℓ 都取不出一段",
            "F1_max_allow": "63/72 = 87.5%", "F7_max_allow": "16/20 = 80.0%",
            "consequence": "unmatched=allow 行不作 go 候选；F1<90% 是算术天花板，不是机制失败",
            "escape": ["G-D（unmatched=deny，闭世界）", "G-G（M2-short，ℓ∈{4,6}；须报误匹配率）"],
            "reporting": "每组合同时给 all（F1 72 / F7 20）与 matchable（F1 63 / F7 16）两个分母，单列 "
                         "structurally_unmatchable（28 片 / 14 对，其中判定侧 13 对 = F1 9 + F7 4，"
                         "另 1 对为 F7 dev）",
        },
        "reporting_contract": {
            "denominators": "每行两个：all（F1 72／F7 20）与 matchable（F1 63／F7 16）；"
                            "被排除的 id 必须逐条列出，不得静默丢对",
            "ambiguous_policy": "同一片段多候选时，同时给 unique（只记声明 cell 命中）与 union"
                                "（全部候选 cell 并入）两口径 ＋ 逐组合 ambiguous 计数；"
                                "只报一个口径则 G3／G5 不过（W0.3 验收 §4 F3）",
        },
        "freeze_policy": {
            "idempotent_write": "三件 config 用 write_json_once 落盘；除 created_at 外内容相同则不重写",
            "freeze_after_last_bootstrap": "FREEZE_W11SPIKE.sha256 在**最后一次** bootstrap 之后生成；"
                                           "旧版归档为 FREEZE_W11SPIKE_v1_w0.3.sha256",
            "grid_entry": "run_grid.py 第一行须 assert check_freeze() == \"OK\"（check_freeze 下一阶段实现）",
            "rerun_after_freeze": "签 SP 后不得再跑 bootstrap；若必须重跑，重签 freeze 并记 DEVIATION_LEDGER 一行",
        },
        "go_no_go": {
            "go": "存在至少一个 **go_eligible=True**（非 oracle、非明文、matcher∉{M0,M1}、"
                  "dest≠cell、denom≠D2）的组合同时满足："
                  "①误拦点估计 ≤30% 且 Wilson 上界 <0.559；②F1 拦截 ≥90% 且 F7 拦截 ≥90%"
                  "（按 matchable 分母报，同时给 all 分母）；③C-A／C-B 拦截 ≥90%；"
                  "④C-C covered 漏匹配 <10%",
            "not_go_if_only": "仅 M0／M1／L2／D2 满足 ⇒ 记「理论上界可行、结构不可行」，不算 go",
            "no_go": "所有 go_eligible 组合都无法同时满足 ⇒ 回写 Thm/Prop4，不进主表",
            "middle": "中间区间如实报数，交负责人签核，不强行归类",
            "dest_cell_ruling": "dest=cell（cell 级写授权）等价于能力隔离，与 R2-8／STATE 行 81 的威胁模型"
                                "（共享 sink、策略不绑实体归属）冲突 ⇒ 只单列为「已知逃逸口」，不进 go",
            "dest_chan_wording": "dest=chan 可进 go，但报告必须写明「两侧几乎不判别」的实测，"
                                 "不得当成有效判别维度",
        },
        "priors_to_be_confronted": PRIORS,
        "controls": {
            "S-1": "良性 38/68 且 120 条拒行逐调用 0 mismatch；F1 72/72 BYPASS；F7 20/20 BYPASS",
            "S-2": "M1 在 exact fragment 上匹配 ≥99%",
            "S-3": "M2-null 匹配 ≤5%",
            "S-4": "M2 与 M1 在 covered transform 上字节一致 ≥99%（**分母=matchable**，"
                   "即 len(content)≥min(ELLS)=8；全片段口径只披露）",
            "S-7": "零模型调用（socket 拦截计数 0）",
        },
        "stop_rules": {
            "DATA_RECONSTRUCTION_FAILED": "重建逐片 content_sha256 对不上 ⇒ 停",
            "BASELINE_MISMATCH": "S-1 逐调用不是 0 mismatch ⇒ 停，先修实现",
            "M2_NOT_IMPLEMENTED": "M2 核心跑不通 ⇒ 转 no-go 或只做 M0/M1 上界",
        },
    }

    rewritten = {
        "inputs.json": common.write_json_once(common.CONFIGS / "inputs.json", inputs),
        "prereg.json": common.write_json_once(common.CONFIGS / "prereg.json", prereg),
        "grid.json": common.write_json_once(common.CONFIGS / "grid.json", {
            "schema": "w11spike.grid/v1", "window": "W11.SPIKE", "created_at": stamp,
            "note": "显式枚举，一行一个组合；threshold 可在签核时调整，调整须重写本文件并重跑",
            "adversary_combos": adv, "combos": grid}),
    }
    print(f"[W11.SPIKE] configs_rewritten={json.dumps(rewritten, ensure_ascii=False)}",
          flush=True)

    body = json.dumps({"inputs": inputs["files"], "grid": len(grid), "theta": theta},
                      ensure_ascii=False, sort_keys=True)
    run_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    run_dir = common.RUNS / f"w11spike-bootstrap-{run_hash}"
    run_dir.mkdir(parents=True, exist_ok=True)

    common.write_json(run_dir / "baseline.json", {
        "schema": "w11spike.baseline/v1", "created_at": stamp,
        "s1_benign": s1, "s1_malicious": s1m, "m0": m0,
        "s4_agreement": s4,
        "match_smoke": match_smoke,
        "w101_cross_check": w101,
        "verdict": "S-1 PASS" if (not s1["mismatch"] and m0["benign_mismatch_n"] == 0) else "FAIL",
    })
    common.write_json(run_dir / "guard.json", common.GUARD.report())
    common.write_json(run_dir / "env.json", {
        "python": sys.version, "platform": platform.platform(),
        "executable": sys.executable,
        "benign_meta": benign.meta, "malicious_meta": mal.meta,
        "grid_combos": len(grid), "adversary_combos": len(adv),
        "go_eligible": len(go_eligible),
    })
    freeze = common.report_freeze()
    common.write_text(run_dir / "log.txt", "\n".join([
        f"window=W11.SPIKE step=1-3 stamp={stamp}",
        f"benign={json.dumps(benign.meta, ensure_ascii=False, sort_keys=True)}",
        f"malicious={json.dumps(mal.meta, ensure_ascii=False, sort_keys=True)}",
        f"S-1 benign denied={s1['denied']}/{s1['tasks']} mismatch={len(s1['mismatch'])}",
        f"S-1 malicious={json.dumps(s1m, ensure_ascii=False, sort_keys=True)}",
        f"M0 benign_points={m0['benign_points']} mismatch={m0['benign_mismatch_n']}",
        f"M0 malicious_r1={json.dumps(m0['malicious_r1'], sort_keys=True)}",
        f"S-4 benign={s4['benign']['byte_identical']}/{s4['benign']['matchable']} "
        f"malicious={s4['malicious']['byte_identical']}/{s4['malicious']['matchable']} "
        f"unmatchable={s4['malicious']['structurally_unmatchable']} "
        f"lens={s4['malicious']['unmatchable_lens']}",
        f"grid={len(grid)} adversary={len(adv)} go_eligible={len(go_eligible)}",
        f"configs_rewritten={json.dumps(rewritten, ensure_ascii=False, sort_keys=True)}",
        f"freeze_status={freeze['status']}",
        f"connect_attempts={common.GUARD.report()['connect_attempts']}",
        "candidate grid NOT run (SP1-SP5 pending)",
    ]) + "\n")
    print(f"[W11.SPIKE] S-4：benign {s4['benign']['byte_identical']}/"
          f"{s4['benign']['matchable']}、malicious {s4['malicious']['byte_identical']}/"
          f"{s4['malicious']['matchable']}、structurally_unmatchable="
          f"{s4['malicious']['structurally_unmatchable']}", flush=True)
    print(f"[W11.SPIKE] freeze_status={freeze['status']}", flush=True)
    print(f"[W11.SPIKE] 落盘：{run_dir}", flush=True)
    print(f"[W11.SPIKE] S-1 = {'PASS' if not s1['mismatch'] else 'FAIL'}；"
          f"候选网格未跑（SP1–SP5 待签）", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
