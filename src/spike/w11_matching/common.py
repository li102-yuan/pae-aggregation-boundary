# -*- coding: utf-8 -*-
"""common.py — W11.SPIKE 的公共设施：路径、摘要、零模型调用证明。

本文件只做三件事，不参与任何判定：
1. 把输入路径与 sha256 固定成一张表（`INPUTS`），供 `inputs.json` 逐条落盘；
2. 提供 `socket_guard()`：进程内拦截一切网络连接并计数——零模型调用的**结构性**证明
   （不是"我们没写模型调用"，而是"这个进程连不出去"）；
3. JSON/CSV 读写一律 UTF-8 + LF。

窗口：`windows/W11.SPIKE_aggregation_matching.md`（spike，不进主表）。
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import socket
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SPIKE = ROOT / "src" / "spike" / "w11_matching"
CONFIGS = ROOT / "configs" / "w11spike"
ANALYSIS = ROOT / "analysis"
RUNS = ROOT / "runs"
REPORTS = ROOT / "reports" / "spike"

# 现行 θ 的唯一来源。`configs/gate/history_v1.json` 的 1.0 是 provisional 暂定值，
# **本模块不读它**（窗口 §2 第 4 条）。
POLICY = ROOT / "configs" / "policy" / "w32_freeze_v1.json"
POLICY_SHA = ROOT / "configs" / "policy" / "w32_freeze_v1.sha256"
THETA_EXPECTED = 0.55

INPUTS = {
    # ---- 良性侧（68 个 holdout 可写任务）----
    "w101_coverage": ROOT / "analysis" / "w101_coverage.csv",
    "carrier_v2": ROOT / "configs" / "w101" / "carrier_v2.json",
    "retail_db": ROOT / "configs" / "sanity" / "data" / "retail_db.json",
    "bench_full": ROOT / "src" / "mcp" / "sanity" / "bench_full.py",
    "carrier_py": ROOT / "src" / "mcp" / "sanity" / "carrier.py",
    "source_py": ROOT / "src" / "mcp" / "sanity" / "source.py",
    "split_w101": ROOT / "configs" / "w101" / "split_w101.json",
    "w101_summary": ROOT / "runs" / "bench-w101-cc8300a4de1aa7bb" / "summary.json",
    # ---- 恶意侧（F1 72 对 / F7 22 对执行、20 判定）----
    "w102_families": ROOT / "configs" / "w102" / "families.json",
    "w102_state_store_v2": ROOT / "configs" / "w102" / "state_store_v2.json",
    "w102_pairs": ROOT / "analysis" / "w102_pairs.csv",
    "w102_summary": ROOT / "analysis" / "w102_summary.json",
    "w102_calls": ROOT / "runs" / "adapt-w102-1b8751c3971054fa" / "calls.jsonl",
    "families_py": ROOT / "src" / "attack" / "adaptive" / "families.py",
    "construct_py": ROOT / "src" / "attack" / "adaptive" / "construct.py",
    "construct_manifest": ROOT / "scenarios" / "s2b_adaptive" / "construct_manifest.json",
    # ---- 参考实现（只读）----
    "ref_py": ROOT / "src" / "observe" / "ref.py",
    "history_py": ROOT / "src" / "gate" / "history.py",
    "canonicalizer_py": ROOT / "src" / "gate" / "canonicalizer.py",
    "policy": POLICY,
}

# 冻结件（G7：这些路径的 git diff 必须为空）
FROZEN_TREES = ("src/gate", "src/observe/ref.py", "configs/gate", "configs/policy",
                "configs/w101", "configs/w102", "configs/sanity")


class SpikeStop(RuntimeError):
    """spike 的停机口（对应窗口 §11 的失败出口）。"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(pathlib.Path(path).read_bytes())


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def dump_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def write_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(obj), encoding="utf-8", newline="\n")


def write_json_once(path, obj, ignore_keys=("created_at",)):
    """（除 `ignore_keys` 外）内容相同则**不写**，保证多次 bootstrap 的字节稳定。

    返回 True 表示真的写了（`configs_rewritten` 记 true），False 表示按原样保留。
    这是 `W0.3` `R-4` 的落地：不修这个，每次重跑都会重写 `created_at`，冻结白签。
    """
    path = pathlib.Path(path)
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        a = {k: v for k, v in old.items() if k not in ignore_keys}
        b = {k: v for k, v in obj.items() if k not in ignore_keys}
        if a == b:
            return False
    write_json(path, obj)
    return True


FREEZE_NAMES = ("inputs.json", "prereg.json", "grid.json")


def report_freeze(names=FREEZE_NAMES, out_dir=None, freeze_name="FREEZE_W11SPIKE.sha256"):
    """把三件当前 sha256 与冻结文件比对 → `OK`／`STALE`／`MISSING`。

    冻结文件格式与 `sha256sum` 兼容（`<hex> *<name>`），因此在
    `configs/w11spike/` 下 `sha256sum -c FREEZE_W11SPIKE.sha256` 可直接复核。
    **只报告，不改冻结**：写冻结是运行者的动作（窗口 §FIX-4 第 4 条）。
    """
    out_dir = pathlib.Path(out_dir) if out_dir is not None else CONFIGS
    lines = [f"{sha256_file(out_dir / name)} *{name}" for name in names]
    freeze_path = out_dir / freeze_name
    if not freeze_path.exists():
        return {"status": "MISSING", "lines": lines, "freeze": str(freeze_path),
                "diff": [f"{name}: 无冻结文件" for name in names]}
    recorded = {}
    for line in freeze_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(" *", 1)
        recorded[name.strip()] = digest.strip()
    diff = []
    for name, line in zip(names, lines):
        current = line.split()[0]
        if recorded.get(name) != current:
            diff.append(f"{name}: {recorded.get(name)} != {current}")
    return {"status": "OK" if not diff else "STALE", "lines": lines,
            "freeze": str(freeze_path), "diff": diff}


def check_freeze():
    """入口断言：freeze 必须 `OK`，否则 `SpikeStop`（窗口 §4 FIX-4 第 5 条）。"""
    rep = report_freeze()
    if rep["status"] != "OK":
        raise SpikeStop(f"冻结不一致（{rep['status']}）：{'; '.join(rep['diff']) or rep['freeze']}")
    return rep


def check_signoff(path=None):
    """入口断言：`SIGNOFF.md` 五格非空且带日期（`D-023`）。"""
    path = pathlib.Path(path) if path is not None else CONFIGS / "SIGNOFF.md"
    if not path.exists():
        raise SpikeStop(f"缺签核文件：{path}")
    text = path.read_text(encoding="utf-8")
    missing = [f"SP{i}" for i in range(1, 6) if f"SP{i} " not in text]
    if missing or "日期：2026" not in text:
        raise SpikeStop(f"签核不完整：缺 {missing} 或日期")
    return {"path": str(path), "sp": [f"SP{i}" for i in range(1, 6)]}


def write_text(path, text):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_csv(path, rows, fields):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(fields)]
    for row in rows:
        cells = []
        for name in fields:
            value = row.get(name, "")
            if value is None:
                cells.append("")
            elif isinstance(value, bool):
                cells.append("1" if value else "0")
            elif isinstance(value, float):
                cells.append(f"{value:.6f}")
            else:
                text = str(value)
                if any(ch in text for ch in ',"\n'):
                    text = '"' + text.replace('"', '""') + '"'
                cells.append(text)
        lines.append(",".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- 零模型调用证明
class _Guard:
    def __init__(self):
        self.connect_attempts = 0
        self.blocked = []
        self._installed = False

    def install(self):
        if self._installed:
            return self
        original = socket.socket.connect
        original_ex = socket.socket.connect_ex
        guard = self

        def connect(sock, address, *a, **kw):
            guard.connect_attempts += 1
            guard.blocked.append(repr(address))
            raise SpikeStop(f"零模型调用约束：进程内禁止网络连接（尝试 {address!r}）")

        def connect_ex(sock, address, *a, **kw):
            guard.connect_attempts += 1
            guard.blocked.append(repr(address))
            return 111  # ECONNREFUSED，不抛异常但也不建立连接

        socket.socket.connect = connect
        socket.socket.connect_ex = connect_ex
        self._installed = True
        return self

    def report(self):
        return {
            "model_calls": 0,
            "connect_attempts": self.connect_attempts,
            "blocked": list(self.blocked),
            "mechanism": "socket.socket.connect / connect_ex 进程内替换为记账+拒绝；"
                         "本包不 import 任何模型客户端",
            "python": sys.version.split()[0],
        }


GUARD = _Guard()

# 模型客户端模块名（只用于自检：本进程从未 import 它们）
_MODEL_MODULES = ("openai", "anthropic", "dashscope", "zhipuai", "requests",
                  "httpx", "aiohttp", "urllib3", "transformers", "torch")


def assert_no_model_imports():
    hits = [name for name in _MODEL_MODULES if name in sys.modules]
    if hits:
        raise SpikeStop(f"零模型调用约束：进程内已 import 模型/网络客户端 {hits}")
    return hits
