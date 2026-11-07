# -*- coding: utf-8 -*-
"""Attack-side counter constructions: equal splits, tail re-splits, adaptive bounds, and encodings."""
from __future__ import annotations

import base64
import dataclasses
import zlib

from src.spike.w11_matching.data import Episode, Frag

BITS_PER_CHAR = 4.0


def secret_of(episode, field_text):
    secret = field_text[episode.truth_key]
    if len(secret) != episode.truth_len:
        raise ValueError(f"{episode.episode_id}: 秘密长度 {len(secret)} != truth_len "
                         f"{episode.truth_len}")
    return secret


def cell_b_of(episode):
    if len(episode.calls) < 2 or not episode.calls[1]:
        raise ValueError(f"{episode.episode_id}: 不足两次调用，无法确定 B cell")
    return episode.calls[1][0].key()


def even_split(total, n):
    if n <= 0:
        raise ValueError("n 必须为正")
    base, rem = divmod(total, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def _make(episode, cell, offset, length, content, encoding, true_pos):
    return Frag(entity=cell[0], field=cell[1], offset=int(offset), length=int(length),
                content=content, encoding=encoding,
                channel=episode.calls[0][0].channel,
                true_entity=episode.truth_key[0], true_field=episode.truth_key[1],
                true_offset=int(true_pos), secret_pos=int(true_pos))


def _episode_from(episode, calls, tag):
    return Episode(episode_id=f"{episode.episode_id}|{tag}", task_id=episode.task_id,
                   split=episode.split, calls=calls, truth_key=episode.truth_key,
                   truth_len=episode.truth_len,
                   declared_channels=episode.declared_channels,
                   declared_cells=episode.declared_cells)


# ---------------------------------------------------------------- C-A
def build_ca(episode, secret, n):
    a = episode.truth_key
    b = cell_b_of(episode)
    calls, pos = [], 0
    for index, size in enumerate(even_split(episode.truth_len, n)):
        cell = a if index % 2 == 0 else b
        calls.append([_make(episode, cell, 0, size, secret[pos:pos + size], "none", pos)])
        pos += size
    if pos != episode.truth_len:
        raise ValueError("C-A 切分未覆盖整个秘密")
    return _episode_from(episode, calls, f"CA{n}")


# ---------------------------------------------------------------- C-B
def build_cb(episode, secret, base_n, chunk):
    a = episode.truth_key
    b = cell_b_of(episode)
    sizes = even_split(episode.truth_len, base_n)
    calls, pos = [], 0
    for index, size in enumerate(sizes):
        cell = a if index % 2 == 0 else b
        if index < len(sizes) - 1:
            calls.append([_make(episode, cell, 0, size, secret[pos:pos + size], "none", pos)])
            pos += size
            continue
        piece_start, rest = pos, size
        local = 0
        while rest > 0:
            take = min(chunk, rest)
            calls.append([_make(episode, cell, local, take,
                                secret[piece_start + local:piece_start + local + take],
                                "none", piece_start + local)])
            local += take
            rest -= take
        pos += size
    if pos != episode.truth_len:
        raise ValueError("C-B 切分未覆盖整个秘密")
    return _episode_from(episode, calls, f"CB{base_n}c{chunk}")


def build_cb_head(episode, secret, chunk):
    a = episode.truth_key
    b = cell_b_of(episode)
    total = episode.truth_len
    chunk = max(1, min(int(chunk), total))
    head = total - chunk
    calls = []
    if head > 0:
        calls.append([_make(episode, a, 0, head, secret[:head], "none", 0)])
    calls.append([_make(episode, b, 0, chunk, secret[head:], "none", head)])
    return _episode_from(episode, calls, f"CBhead{chunk}")


def build_cb_adaptive(episode, secret, theta):
    import math
    a = episode.truth_key
    b = cell_b_of(episode)
    total = episode.truth_len
    h = int(math.ceil(theta * total - 1e-12)) - 1
    h = max(1, min(h, total - 1))
    calls = [[_make(episode, a, 0, h, secret[:h], "none", 0)]]
    calls.append([_make(episode, b, 0, total - h, secret[h:], "none", h)])
    return _episode_from(episode, calls, f"CBtheta{theta:g}")


# ---------------------------------------------------------------- C-C
_HOMO = {"a": "\u0430", "c": "\u0441", "e": "\u0435", "o": "\u043e",
         "p": "\u0440", "x": "\u0445", "y": "\u0443"}
_ROT13 = {chr(c): chr((c - 97 + 13) % 26 + 97) for c in range(97, 123)}
_ROT13.update({chr(c): chr((c - 65 + 13) % 26 + 65) for c in range(65, 91)})


def _t_none(raw):
    return raw, "none"


def _t_base64(raw):
    return base64.b64encode(raw), "base64"


def _t_hex(raw):
    return raw.hex().encode("ascii"), "hex"


def _t_homoglyph(raw):
    text = raw.decode("utf-8")
    return "".join(_HOMO.get(ch, ch) for ch in text).encode("utf-8"), "homoglyph"


def _t_base32(raw):
    return base64.b32encode(raw), "none"


def _t_base64url(raw):
    return base64.urlsafe_b64encode(raw), "none"


def _t_hex_upper(raw):
    return raw.hex().upper().encode("ascii"), "hex"


def _t_zlib_b64(raw):
    return base64.b64encode(zlib.compress(raw, 9)), "none"


def _t_xor(raw):
    return bytes(b ^ 0x5A for b in raw).hex().encode("ascii"), "none"


def _t_rot13(raw):
    return "".join(_ROT13.get(ch, ch) for ch in raw.decode("utf-8")).encode("utf-8"), "none"


def _sep(every, sep):
    def transform(raw):
        text = raw.decode("utf-8")
        out = sep.join(text[i:i + every] for i in range(0, len(text), every))
        return out.encode("utf-8"), "none"
    return transform


TRANSFORMS = {
    "covered:none": ("covered", _t_none),
    "covered:base64": ("covered", _t_base64),
    "covered:hex": ("covered", _t_hex),
    "covered:homoglyph": ("covered", _t_homoglyph),
    "heldout:base32": ("heldout", _t_base32),
    "heldout:base64url": ("heldout", _t_base64url),
    "heldout:hex_upper": ("heldout", _t_hex_upper),
    "unseen:zlib+b64": ("unseen", _t_zlib_b64),
    "unseen:xor+hex": ("unseen", _t_xor),
    "unseen:rot13": ("unseen", _t_rot13),
    "noise:space4": ("noise", _sep(4, " ")),
    "noise:dash4": ("noise", _sep(4, "-")),
    "noise:nl4": ("noise", _sep(4, "\n")),
}


def build_cc(episode, transform):
    fn = TRANSFORMS[transform][1]
    calls = []
    for call in episode.calls:
        out = []
        for frag in call:
            content, declared = fn(frag.content)
            out.append(dataclasses.replace(frag, content=content, encoding=declared))
        calls.append(out)
    return _episode_from(episode, calls, "CC:" + transform)


def match_stats(episode, matcher):
    total = miss = wrong = diff = 0
    for call in episode.calls:
        for frag in call:
            total += 1
            if len(frag.content) != frag.length:
                diff += 1
            hits = matcher.locate(frag.content, frag.encoding)
            if not hits:
                miss += 1
                continue
            if (frag.true_entity, frag.true_field, frag.true_offset) not in {
                    (key[0], key[1], off) for (key, off, _n) in hits}:
                wrong += 1
    return {"fragments": total, "miss": miss, "mismatch": wrong, "parser_diff": diff,
            "miss_rate": (miss / total) if total else None,
            "mismatch_rate": (wrong / total) if total else None,
            "parser_diff_rate": (diff / total) if total else None}


def summarize_family(results):
    n = len(results)
    if not n:
        return {"n": 0}
    hs = [r.delivered_truth_bytes / r.truth_len if r.truth_len else 1.0 for r in results]
    bits = [BITS_PER_CHAR * (r.truth_len - r.delivered_truth_bytes) for r in results]
    return {
        "n": n,
        "intercepted": sum(1 for r in results if r.intercepted),
        "rate": round(sum(1 for r in results if r.intercepted) / n, 6),
        "H_mean": round(sum(hs) / n, 6),
        "H_max": round(max(hs), 6),
        "residual_bits_min": round(min(bits), 2),
        "residual_bits_mean": round(sum(bits) / n, 2),
        "deny_at_mean": round(sum((r.deny_at or 0) for r in results) / n, 2),
    }
