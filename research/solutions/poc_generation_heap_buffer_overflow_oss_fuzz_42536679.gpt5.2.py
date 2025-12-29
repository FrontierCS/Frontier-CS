import os
import io
import re
import tarfile
import zipfile
import struct
import zlib
from collections import defaultdict
from typing import Dict, Optional, Tuple


def _u16le(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _u16be(x: int) -> bytes:
    return struct.pack(">H", x & 0xFFFF)


def _u32le(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _u32be(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def _i32le(x: int) -> bytes:
    return struct.pack("<i", int(x))


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(typ)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return _u32be(len(data)) + typ + data + _u32be(crc)


def craft_png(width: int = 0, height: int = 1) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _u32be(width) + _u32be(height) + bytes([8, 0, 0, 0, 0])
    raw = b"\x00" * height
    comp = zlib.compress(raw, level=9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", comp) + _png_chunk(b"IEND", b"")


def craft_psd(width: int = 0, height: int = 1) -> bytes:
    # Minimal PSD: header + empty sections + compression=raw + no image data if width*height==0.
    out = bytearray()
    out += b"8BPS"
    out += _u16be(1)
    out += b"\x00" * 6
    out += _u16be(1)  # channels
    out += _u32be(height)
    out += _u32be(width)
    out += _u16be(8)  # depth
    out += _u16be(1)  # color mode: grayscale
    out += _u32be(0)  # color mode data length
    out += _u32be(0)  # image resources length
    out += _u32be(0)  # layer/mask info length
    out += _u16be(0)  # compression: raw
    return bytes(out)


def craft_bmp(width: int = 0, height: int = 1) -> bytes:
    # 24bpp BITMAPINFOHEADER, no pixel data if width==0
    bfType = b"BM"
    bfOffBits = 14 + 40
    bfSize = bfOffBits
    out = bytearray()
    out += bfType
    out += _u32le(bfSize)
    out += _u16le(0)
    out += _u16le(0)
    out += _u32le(bfOffBits)
    out += _u32le(40)  # biSize
    out += _i32le(width)
    out += _i32le(height)
    out += _u16le(1)  # planes
    out += _u16le(24)  # bpp
    out += _u32le(0)  # compression
    out += _u32le(0)  # sizeimage
    out += _i32le(0)  # xppm
    out += _i32le(0)  # yppm
    out += _u32le(0)  # clrused
    out += _u32le(0)  # clrimportant
    return bytes(out)


def craft_tga(width: int = 0, height: int = 1) -> bytes:
    # Uncompressed true-color, no data if width==0
    out = bytearray(18)
    out[0] = 0  # id length
    out[1] = 0  # color map type
    out[2] = 2  # image type: uncompressed true-color
    out[12:14] = _u16le(width)
    out[14:16] = _u16le(height)
    out[16] = 24  # pixel depth
    out[17] = 0
    return bytes(out)


def craft_qoi(width: int = 0, height: int = 1) -> bytes:
    # Header + end marker. With width==0, pixels=0.
    out = bytearray()
    out += b"qoif"
    out += _u32be(width)
    out += _u32be(height)
    out += bytes([3, 0])  # channels=3, colorspace=0
    out += b"\x00\x00\x00\x00\x00\x00\x00\x01"  # end marker
    return bytes(out)


def craft_pnm_p6(width: int = 0, height: int = 1) -> bytes:
    return f"P6\n{width} {height}\n255\n".encode("ascii")


def craft_dds(width: int = 0, height: int = 1) -> bytes:
    # Minimal DDS header with no pixel format specifics (likely rejected by strict parsers)
    # Kept as fallback only.
    out = bytearray()
    out += b"DDS "
    out += _u32le(124)  # size
    out += _u32le(0x0002100F)  # flags: caps|height|width|pixelformat|mipmapcount|linearsize (generic)
    out += _u32le(height)
    out += _u32le(width)
    out += _u32le(0)  # pitch or linear size
    out += _u32le(0)  # depth
    out += _u32le(0)  # mipmap count
    out += b"\x00" * (11 * 4)  # reserved1
    # pixel format (32 bytes)
    out += _u32le(32)  # pfSize
    out += _u32le(0)  # pfFlags
    out += _u32le(0)  # fourcc
    out += _u32le(0)  # rgbBitCount
    out += _u32le(0)  # rMask
    out += _u32le(0)  # gMask
    out += _u32le(0)  # bMask
    out += _u32le(0)  # aMask
    # caps (16 bytes)
    out += _u32le(0x1000)  # caps1: texture
    out += _u32le(0)
    out += _u32le(0)
    out += _u32le(0)
    out += _u32le(0)  # reserved2
    return bytes(out)


def guess_format(data: bytes, name: str = "") -> Optional[str]:
    if len(data) >= 8 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(data) >= 6 and (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
        return "gif"
    if len(data) >= 2 and data.startswith(b"\xFF\xD8"):
        return "jpg"
    if len(data) >= 2 and data.startswith(b"BM"):
        return "bmp"
    if len(data) >= 4 and data.startswith(b"8BPS"):
        return "psd"
    if len(data) >= 4 and data.startswith(b"DDS "):
        return "dds"
    if len(data) >= 4 and data.startswith(b"qoif"):
        return "qoi"
    if len(data) >= 4 and (data.startswith(b"II*\x00") or data.startswith(b"MM\x00*")):
        return "tiff"
    if len(data) >= 2 and data[:2] in (b"P1", b"P2", b"P3", b"P4", b"P5", b"P6"):
        return "pnm"
    l = data.lstrip()
    if l.startswith(b"<svg") or l.startswith(b"<?xml"):
        # could be SVG; only return if name hints
        if name.lower().endswith(".svg") or b"<svg" in l[:512]:
            return "svg"
    ext = os.path.splitext(name.lower())[1]
    if ext in (".png", ".apng"):
        return "png"
    if ext in (".jpg", ".jpeg"):
        return "jpg"
    if ext in (".bmp",):
        return "bmp"
    if ext in (".psd",):
        return "psd"
    if ext in (".tif", ".tiff"):
        return "tiff"
    if ext in (".qoi",):
        return "qoi"
    if ext in (".dds",):
        return "dds"
    if ext in (".pnm", ".ppm", ".pgm", ".pbm"):
        return "pnm"
    if ext in (".tga",):
        return "tga"
    if ext in (".gif",):
        return "gif"
    if ext in (".svg",):
        return "svg"
    return None


def mutate_png_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 8 + 8 + 13 + 4:
        return None
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    off = 8
    if off + 8 > len(data):
        return None
    length = struct.unpack(">I", data[off:off + 4])[0]
    typ = data[off + 4:off + 8]
    if typ != b"IHDR" or length != 13:
        return None
    if off + 8 + 13 + 4 > len(data):
        return None
    chunk_data = bytearray(data[off + 8:off + 8 + 13])
    chunk_data[0:4] = b"\x00\x00\x00\x00"
    new_crc = zlib.crc32(b"IHDR")
    new_crc = zlib.crc32(chunk_data, new_crc) & 0xFFFFFFFF
    out = bytearray(data)
    out[off + 8:off + 8 + 13] = chunk_data
    out[off + 8 + 13:off + 8 + 13 + 4] = _u32be(new_crc)
    return bytes(out)


def mutate_psd_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 26:
        return None
    if data[0:4] != b"8BPS":
        return None
    out = bytearray(data)
    out[18:22] = b"\x00\x00\x00\x00"
    return bytes(out)


def mutate_bmp_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 26:
        return None
    if data[0:2] != b"BM":
        return None
    if len(data) < 14 + 4:
        return None
    dib_size = struct.unpack("<I", data[14:18])[0]
    if dib_size < 40 or len(data) < 14 + dib_size:
        return None
    out = bytearray(data)
    out[18:22] = _i32le(0)
    return bytes(out)


def mutate_tga_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 18:
        return None
    out = bytearray(data)
    out[12:14] = _u16le(0)
    return bytes(out)


def mutate_qoi_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 14:
        return None
    if data[0:4] != b"qoif":
        return None
    out = bytearray(data)
    out[4:8] = b"\x00\x00\x00\x00"
    return bytes(out)


def mutate_dds_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 4 + 124:
        return None
    if data[0:4] != b"DDS ":
        return None
    out = bytearray(data)
    out[16:20] = _u32le(0)
    return bytes(out)


def mutate_jpg_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 4:
        return None
    if data[0:2] != b"\xFF\xD8":
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
        if marker in (0xD8, 0xD9) or (0xD0 <= marker <= 0xD7):
            continue
        if i + 2 > n:
            break
        seglen = (out[i] << 8) | out[i + 1]
        if seglen < 2 or i + seglen > n:
            break
        is_sof = marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)
        if is_sof and seglen >= 8:
            # i points to length; layout: len(2), precision(1), height(2), width(2), ...
            # Set width=0, keep height as-is
            wpos = i + 2 + 1 + 2
            if wpos + 2 <= n:
                out[wpos:wpos + 2] = b"\x00\x00"
                return bytes(out)
        i += seglen
    return None


def _tiff_set_tag_value(out: bytearray, endian: str, entry_off: int, typ: int, count: int, value: int) -> bool:
    if count != 1:
        return False
    if endian == "<":
        pack_u16 = lambda x: struct.pack("<H", x & 0xFFFF)
        pack_u32 = lambda x: struct.pack("<I", x & 0xFFFFFFFF)
    else:
        pack_u16 = lambda x: struct.pack(">H", x & 0xFFFF)
        pack_u32 = lambda x: struct.pack(">I", x & 0xFFFFFFFF)

    # entry: tag(2), type(2), count(4), value_or_offset(4)
    if typ == 3:  # SHORT
        out[entry_off + 8:entry_off + 12] = pack_u16(value) + b"\x00\x00"
        return True
    if typ == 4:  # LONG
        out[entry_off + 8:entry_off + 12] = pack_u32(value)
        return True
    return False


def mutate_tiff_width_zero(data: bytes) -> Optional[bytes]:
    if len(data) < 8:
        return None
    if data[:4] == b"II*\x00":
        endian = "<"
    elif data[:4] == b"MM\x00*":
        endian = ">"
    else:
        return None
    out = bytearray(data)
    ifd_off = struct.unpack(endian + "I", out[4:8])[0]
    if ifd_off + 2 > len(out):
        return None
    nent = struct.unpack(endian + "H", out[ifd_off:ifd_off + 2])[0]
    entries_off = ifd_off + 2
    if entries_off + 12 * nent > len(out):
        return None
    changed = False
    for k in range(nent):
        eoff = entries_off + 12 * k
        tag, typ = struct.unpack(endian + "HH", out[eoff:eoff + 4])
        count = struct.unpack(endian + "I", out[eoff + 4:eoff + 8])[0]
        if tag == 256:  # ImageWidth
            if _tiff_set_tag_value(out, endian, eoff, typ, count, 0):
                changed = True
    return bytes(out) if changed else None


def mutate_pnm_width_zero(data: bytes) -> Optional[bytes]:
    # Replace width in header with 0; difficult generally. Use crafted instead.
    return None


def mutate_svg_width_zero(data: bytes) -> Optional[bytes]:
    try:
        s = data.decode("utf-8", "ignore")
    except Exception:
        return None
    m = re.search(r"<svg\b", s, flags=re.IGNORECASE)
    if not m:
        return None
    # Add/replace width="0"
    # Replace first width attribute in <svg ...> if present, else insert.
    start = m.start()
    gt = s.find(">", start)
    if gt == -1:
        return None
    tag = s[start:gt + 1]
    if re.search(r"\bwidth\s*=", tag, flags=re.IGNORECASE):
        tag2 = re.sub(r'(\bwidth\s*=\s*)(["\'])(.*?)\2', r'\1\2' + "0" + r'\2', tag, count=1, flags=re.IGNORECASE)
    else:
        tag2 = tag[:-1] + ' width="0"' + tag[-1:]
    s2 = s[:start] + tag2 + s[gt + 1:]
    return s2.encode("utf-8")


MUTATORS = {
    "png": mutate_png_width_zero,
    "psd": mutate_psd_width_zero,
    "bmp": mutate_bmp_width_zero,
    "tga": mutate_tga_width_zero,
    "qoi": mutate_qoi_width_zero,
    "dds": mutate_dds_width_zero,
    "jpg": mutate_jpg_width_zero,
    "tiff": mutate_tiff_width_zero,
    "pnm": mutate_pnm_width_zero,
    "svg": mutate_svg_width_zero,
}

CRAFTERS = {
    "png": lambda: craft_png(0, 1),
    "psd": lambda: craft_psd(0, 1),
    "bmp": lambda: craft_bmp(0, 1),
    "tga": lambda: craft_tga(0, 1),
    "qoi": lambda: craft_qoi(0, 1),
    "pnm": lambda: craft_pnm_p6(0, 1),
    "dds": lambda: craft_dds(0, 1),
}


def score_formats_from_fuzzer_text(fuzzer_texts: Tuple[str, ...], fuzzer_names: Tuple[str, ...]) -> Dict[str, int]:
    txt = "\n".join(fuzzer_texts).lower()
    scores = defaultdict(int)

    def add(fmt: str, pats) -> None:
        s = 0
        for p in pats:
            s += txt.count(p)
        scores[fmt] += s

    add("png", ["png", "ihdr", "libpng", "spng"])
    add("jpg", ["jpeg", "jpeglib", "jfif", "mjpe", "jpg"])
    add("bmp", ["bmp", "bitmap"])
    add("tiff", ["tiff", "tif", "tiffio"])
    add("gif", ["gif"])
    add("psd", ["psd", "8bps", "photoshop"])
    add("tga", ["tga", "targa"])
    add("qoi", ["qoi", "qoif"])
    add("dds", ["dds"])
    add("pnm", ["pnm", "ppm", "pgm", "pbm", "pnmread"])
    add("svg", ["svg", "librsvg", "rsvg", "cairo", "xml"])

    for n in fuzzer_names:
        ln = n.lower()
        for fmt in ("png", "jpg", "bmp", "tiff", "gif", "psd", "tga", "qoi", "dds", "pnm", "svg"):
            if fmt in ln:
                scores[fmt] += 5
        if "jpeg" in ln:
            scores["jpg"] += 5
        if "tif" in ln:
            scores["tiff"] += 3

    return dict(scores)


def pick_best_format(scores: Dict[str, int], available: Dict[str, Tuple[int, bytes, str]]) -> str:
    if scores:
        fmts = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        for fmt, sc in fmts:
            if sc <= 0:
                break
            if fmt in available:
                return fmt
        if fmts and fmts[0][1] > 0:
            return fmts[0][0]
    if available:
        # Prefer smallest available sample among formats we can mutate/craft.
        best = None
        for fmt, (sz, _, _) in available.items():
            if fmt in MUTATORS or fmt in CRAFTERS:
                if best is None or sz < best[0]:
                    best = (sz, fmt)
        if best is not None:
            return best[1]
        return min(available.items(), key=lambda kv: kv[1][0])[0]
    return "png"


class Solution:
    def solve(self, src_path: str) -> bytes:
        fuzzer_texts = []
        fuzzer_names = []

        # available[fmt] = (size, bytes, origin_name)
        available: Dict[str, Tuple[int, bytes, str]] = {}

        code_exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
        image_like_exts = {
            ".png", ".apng", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".psd", ".tga",
            ".qoi", ".dds", ".pnm", ".ppm", ".pgm", ".pbm", ".svg"
        }

        def maybe_store_sample(fmt: str, data: bytes, origin: str) -> None:
            sz = len(data)
            prev = available.get(fmt)
            if prev is None or sz < prev[0]:
                available[fmt] = (sz, data, origin)

        def process_zip_bytes(zb: bytes, zip_origin: str) -> None:
            try:
                zf = zipfile.ZipFile(io.BytesIO(zb))
            except Exception:
                return
            try:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > 2_000_000:
                        continue
                    name = zi.filename
                    ext = os.path.splitext(name.lower())[1]
                    if ext not in image_like_exts:
                        continue
                    try:
                        data = zf.read(zi)
                    except Exception:
                        continue
                    fmt = guess_format(data[:256], name) or guess_format(data[:64], name)
                    if fmt is None:
                        continue
                    maybe_store_sample(fmt, data, f"{zip_origin}:{name}")
            finally:
                try:
                    zf.close()
                except Exception:
                    pass

        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                lname = name.lower()
                ext = os.path.splitext(lname)[1]

                if ext == ".zip" and m.size > 0 and m.size <= 20_000_000:
                    if any(k in lname for k in ("seed", "corpus", "fuzz", "test")):
                        try:
                            f = tf.extractfile(m)
                            if f is not None:
                                zb = f.read()
                                process_zip_bytes(zb, name)
                        except Exception:
                            pass
                    continue

                if ext in code_exts and m.size > 0 and m.size <= 1_500_000 and ("fuzz" in lname or "fuzzer" in lname):
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = f.read()
                        t = b.decode("utf-8", "ignore")
                        if ("LLVMFuzzerTestOneInput" in t) or ("FuzzerTestOneInput" in t) or ("FuzzedDataProvider" in t):
                            fuzzer_texts.append(t)
                            fuzzer_names.append(name)
                    except Exception:
                        pass
                    continue

                if ext in image_like_exts and m.size > 0 and m.size <= 2_000_000:
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        # read a small prefix to guess
                        prefix = f.read(256)
                        fmt = guess_format(prefix, name)
                        if fmt is None:
                            # likely tga by extension
                            if ext == ".tga":
                                fmt = "tga"
                            else:
                                continue
                        # need full bytes for mutation/crafting
                        rest = f.read()
                        data = prefix + rest
                        maybe_store_sample(fmt, data, name)
                    except Exception:
                        pass
                    continue

        scores = score_formats_from_fuzzer_text(tuple(fuzzer_texts), tuple(fuzzer_names))
        fmt = pick_best_format(scores, available)

        # Prefer mutating an existing sample (except often better to craft minimal PNG).
        if fmt in available and fmt in MUTATORS and fmt != "png":
            _, base, _ = available[fmt]
            mutated = MUTATORS[fmt](base)
            if mutated is not None and len(mutated) > 0:
                return mutated

        # If png, try crafting minimal valid png with zero width, and also try mutating sample as backup
        if fmt == "png":
            return craft_png(0, 1)

        # If we have a sample for fmt but mutation failed or fmt has no mutator, still try crafting.
        crafter = CRAFTERS.get(fmt)
        if crafter is not None:
            return crafter()

        # Fallback: try mutate any available sample with a known mutator, preferring smallest.
        for f2, (sz, base, _) in sorted(available.items(), key=lambda kv: kv[1][0]):
            mut = MUTATORS.get(f2)
            if mut is None:
                continue
            mutated = mut(base)
            if mutated is not None and len(mutated) > 0:
                return mutated

        # Final fallback: minimal crafted PSD then PNG
        return craft_psd(0, 1) + b""