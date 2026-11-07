# -*- coding: utf-8 -*-
"""Content-attribution matchers: plaintext, keyed l-gram index, and short-window variant."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os

from src.observe.ref import normalize_homoglyphs

SUPPORTED_ENC = ("none", "base64", "hex", "homoglyph")
ELLS = (8, 16, 32)


def _try_decode(raw: bytes, encoding: str):
    if encoding == "none":
        return raw
    if encoding == "base64":
        try:
            return base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            return None
    if encoding == "hex":
        try:
            return bytes.fromhex(raw.decode("ascii"))
        except (ValueError, UnicodeDecodeError):
            return None
    if encoding == "homoglyph":
        try:
            return normalize_homoglyphs(raw.decode("utf-8")).encode("utf-8")
        except UnicodeDecodeError:
            return None
    return None


def normalizations(raw: bytes, declared: str, mode: str):
    order = [declared] if mode == "declared" else list(SUPPORTED_ENC)
    if declared not in order:
        order = [declared] + order
    out, seen = [], set()
    for name in order:
        got = _try_decode(raw, name)
        if got is not None and got not in seen:
            seen.add(got)
            out.append((name, got))
    return out


# ---------------------------------------------------------------- M1
class PlaintextMatcher:

    name = "M1"

    def __init__(self, field_text, norm="all4"):
        self.fields = field_text
        self.norm = norm
        self.queries = 0
        self.matched = 0
        self._order = sorted(field_text)
        self._cache = {}

    def locate(self, raw: bytes, declared: str):
        ck = (raw, declared)
        if ck in self._cache:
            return self._cache[ck]
        hits = self._locate(raw, declared)
        self._cache[ck] = hits
        return hits

    def _locate(self, raw: bytes, declared: str):
        self.queries += 1
        hits = []
        for _name, needle in normalizations(raw, declared, self.norm):
            if not needle:
                continue
            for key in self._order:
                hay = self.fields[key]
                start = hay.find(needle)
                while start >= 0:
                    hits.append((key, start, len(needle)))
                    start = hay.find(needle, start + 1)
            if hits:
                break
        uniq = sorted(set(hits))
        if uniq:
            self.matched += 1
        return uniq


# ---------------------------------------------------------------- M2
class FingerprintMatcher:

    name = "M2"

    def __init__(self, field_text, ells=ELLS, norm="all4", key: bytes | None = None,
                 build_index: bool = True):
        self.fields = field_text
        self.ells = tuple(sorted(ells, reverse=True))
        self.norm = norm
        self.key = key if key is not None else os.urandom(32)
        self.key_sha256 = hashlib.sha256(self.key).hexdigest()
        self.build_index = build_index
        self.index = {}
        self.hmac_calls = 0
        self.index_entries = 0
        self.queries = 0
        self.matched = 0
        self.ambiguous = 0
        self._cache = {}
        if build_index:
            self._build()

    def _mac(self, data: bytes) -> bytes:
        self.hmac_calls += 1
        return hmac.new(self.key, data, hashlib.sha256).digest()

    def _build(self):
        for ell in self.ells:
            table = {}
            for key in sorted(self.fields):
                text = self.fields[key]
                if len(text) < ell:
                    continue
                for offset in range(0, len(text) - ell + 1):
                    digest = self._mac(text[offset:offset + ell])
                    table.setdefault(digest, []).append((key, offset))
            self.index[ell] = table
            self.index_entries += sum(len(v) for v in table.values())

    def locate(self, raw: bytes, declared: str):
        ck = (raw, declared)
        if ck in self._cache:
            return self._cache[ck]
        hits = self._locate(raw, declared)
        self._cache[ck] = hits
        return hits

    def _locate(self, raw: bytes, declared: str):
        self.queries += 1
        if not self.build_index:
            return []
        best = []
        for _name, needle in normalizations(raw, declared, self.norm):
            n = len(needle)
            if n == 0:
                continue
            for ell in self.ells:
                if n < ell:
                    continue
                table = self.index[ell]
                votes = {}
                for pos in range(0, n - ell + 1):
                    for (key, offset) in table.get(self._mac(needle[pos:pos + ell]), ()):
                        start = offset - pos
                        if start < 0:
                            continue
                        votes[(key, start)] = votes.get((key, start), 0) + 1
                need = n - ell + 1
                accepted = sorted(k for k, v in votes.items() if v == need)
                if accepted:
                    best = [(key, start, n) for (key, start) in accepted]
                    break
            if best:
                break
        if len(best) > 1:
            self.ambiguous += 1
        if best:
            self.matched += 1
        return best


class NullMatcher(FingerprintMatcher):

    name = "M2-null"

    def __init__(self, field_text, ells=ELLS, norm="all4"):
        super().__init__(field_text, ells=ells, norm=norm, build_index=False)


def build(name, field_text, norm="all4", ells=ELLS):
    if name == "M1":
        return PlaintextMatcher(field_text, norm=norm)
    if name == "M2":
        return FingerprintMatcher(field_text, ells=ells, norm=norm)
    if name == "M2-null":
        return NullMatcher(field_text, norm=norm)
    if name == "M2-short":
        return FingerprintMatcher(field_text, ells=(4, 6) + tuple(ells), norm=norm)
    raise ValueError(f"未知匹配臂：{name}")
