# -*- coding: utf-8 -*-
"""Shared paths, hashing, and freeze/sign-off checks."""
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

POLICY = ROOT / "configs" / "policy" / "w32_freeze_v1.json"
POLICY_SHA = ROOT / "configs" / "policy" / "w32_freeze_v1.sha256"
THETA_EXPECTED = 0.55

INPUTS = {
    "w101_coverage": ROOT / "analysis" / "w101_coverage.csv",
    "carrier_v2": ROOT / "configs" / "w101" / "carrier_v2.json",
    "retail_db": ROOT / "configs" / "sanity" / "data" / "retail_db.json",
    "bench_full": ROOT / "src" / "mcp" / "sanity" / "bench_full.py",
    "carrier_py": ROOT / "src" / "mcp" / "sanity" / "carrier.py",
    "source_py": ROOT / "src" / "mcp" / "sanity" / "source.py",
    "split_w101": ROOT / "configs" / "w101" / "split_w101.json",
    "w101_summary": ROOT / "runs" / "bench-w101-cc8300a4de1aa7bb" / "summary.json",
    "w102_families": ROOT / "configs" / "w102" / "families.json",
    "w102_state_store_v2": ROOT / "configs" / "w102" / "state_store_v2.json",
    "w102_pairs": ROOT / "analysis" / "w102_pairs.csv",
    "w102_summary": ROOT / "analysis" / "w102_summary.json",
    "w102_calls": ROOT / "runs" / "adapt-w102-1b8751c3971054fa" / "calls.jsonl",
    "families_py": ROOT / "src" / "attack" / "adaptive" / "families.py",
    "construct_py": ROOT / "src" / "attack" / "adaptive" / "construct.py",
    "construct_manifest": ROOT / "scenarios" / "s2b_adaptive" / "construct_manifest.json",
    "ref_py": ROOT / "src" / "observe" / "ref.py",
    "history_py": ROOT / "src" / "gate" / "history.py",
    "canonicalizer_py": ROOT / "src" / "gate" / "canonicalizer.py",
    "policy": POLICY,
}

FROZEN_TREES = ("src/gate", "src/observe/ref.py", "configs/gate", "configs/policy",
                "configs/w101", "configs/w102", "configs/sanity")


class SpikeStop(RuntimeError):
        pass


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
    rep = report_freeze()
    if rep["status"] != "OK":
        raise SpikeStop(f"冻结不一致（{rep['status']}）：{'; '.join(rep['diff']) or rep['freeze']}")
    return rep


def check_signoff(path=None):
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
            return 111

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

_MODEL_MODULES = ("openai", "anthropic", "dashscope", "zhipuai", "requests",
                  "httpx", "aiohttp", "urllib3", "transformers", "torch")


def assert_no_model_imports():
    hits = [name for name in _MODEL_MODULES if name in sys.modules]
    if hits:
        raise SpikeStop(f"零模型调用约束：进程内已 import 模型/网络客户端 {hits}")
    return hits
